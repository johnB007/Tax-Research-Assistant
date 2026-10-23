from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import json

from tax_agent.agent import FilingProfile, ReviewInput, answer_deduction_review, answer_tax_question, build_review_brief
from tax_agent.config import get_settings
from tax_agent.law_ingest import build_law_index, get_index_status, get_recent_source_changes
from tax_agent.states_config import STATES_AVAILABLE, get_states_for_publication
from tax_agent.statement_parser import (
    TaxReturnSummary,
    Transaction,
    get_pdf_extraction_status,
    parse_tax_form_line_items,
    parse_tax_return_summary,
    parse_statement,
    summarize_tax_form_coverage,
    summarize_tax_form_line_items,
    summarize_transactions,
    summarize_tax_return_summaries,
)


def _save_extract_csv(df: pd.DataFrame, source_stem: str, beside: Path | None = None) -> Path:
    if beside is None:
        save_dir = settings.data_dir / "extracts"
    elif beside.suffix:
        save_dir = beside.parent
    else:
        save_dir = beside
    save_dir.mkdir(parents=True, exist_ok=True)
    out_path = save_dir / f"{source_stem}_extracted.csv"
    df.to_csv(out_path, index=False)
    return out_path


def _save_uploaded_file(file_obj, destination_dir: Path) -> Path:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / Path(file_obj.name).name
    destination.write_bytes(file_obj.read())
    return destination

settings = get_settings()

# Load user configuration
config_file = Path("config.json")
if config_file.exists():
    with open(config_file) as f:
        user_config = json.load(f)
else:
    user_config = {"selected_states": ["SC"]}

st.set_page_config(page_title="Tax Research Agent", layout="wide")

st.title("Tax Research Agent")

# State selector in sidebar (moved to top for visibility)
st.sidebar.header("Jurisdiction & Filing")
state_options = list(STATES_AVAILABLE.keys())
initial_state_idx = (
    state_options.index(user_config.get("selected_states", ["SC"])[0])
    if user_config.get("selected_states")
    else 0
)
selected_state = st.sidebar.selectbox(
    "Select your state",
    options=state_options,
    index=initial_state_idx,
    help="Loads state-specific tax sources and payment portal links.",
)

# Save state preference
if selected_state != user_config.get("selected_states", ["SC"])[0]:
    user_config["selected_states"] = [selected_state]
    with open(config_file, "w") as f:
        json.dump(user_config, f, indent=2)
    st.sidebar.success(f"Saved {selected_state} as your state. Refresh to load new sources.")

# Load crawl roots for selected state
if selected_state not in STATES_AVAILABLE:
    selected_state = "SC"

# Get fresh crawl roots from the configuration
crawl_roots_raw = STATES_AVAILABLE[selected_state]["crawl_roots"]
current_crawl_roots = list(crawl_roots_raw)

# Build mapping of root names for selectbox, with fallback handling
root_names = []
roots_by_name = {}
for root in current_crawl_roots:
    name = getattr(root, 'name', f'Root from {root.jurisdiction}' if hasattr(root, 'jurisdiction') else 'Unknown Root')
    root_names.append(name)
    roots_by_name[name] = root

st.caption(
    f"Research support for {selected_state} and Federal IRS tax questions, with statement upload and expense mapping."
)

st.warning(
    "This tool is for education and research. It is not legal, tax, or accounting advice. "
    "Use a licensed CPA or tax attorney for final filing decisions."
)

if not settings.law_db_path.exists():
    st.info(
        "Law index is not built yet. Run Build law index to enable broad citation coverage across IRS and South Carolina sub pages."
    )

if "transactions" not in st.session_state:
    st.session_state.transactions = []
if "tax_review_root_dir" not in st.session_state:
    st.session_state.tax_review_root_dir = str(settings.data_dir / "tax_review")

index_status = get_index_status()
last_crawled_at = index_status.get("last_crawled_at", "")
if last_crawled_at:
    st.caption(
        f"Legal sources last crawled: {last_crawled_at} | Sources: {index_status.get('source_count', 0)} | Chunks: {index_status.get('chunk_count', 0)}"
    )
else:
    st.caption("Legal sources last crawled: unavailable")

st.sidebar.header("Filing profile")
filing_year = st.sidebar.selectbox(
    "Filing year",
    options=["2026", "2025", "2024", "2023"],
    index=0,
)
federal_filing_status = st.sidebar.selectbox(
    "Federal filing status",
    options=[
        "Married filing jointly",
        "Married filing separately",
        "Single",
        "Head of household",
    ],
    index=0,
)
state_residency = st.sidebar.text_input("State residency", value="South Carolina")
primary_has_w2_only = st.sidebar.checkbox("Primary has W2 income only", value=False)
has_llc = st.sidebar.checkbox("Spouse has LLC", value=True)
has_s_corp = st.sidebar.checkbox("Spouse has S Corp", value=True)
pays_quarterly_estimates = st.sidebar.checkbox("Quarterly estimates paid", value=True)

profile = FilingProfile(
    filing_year=filing_year,
    federal_filing_status=federal_filing_status,
    state_residency=state_residency,
    has_llc=has_llc,
    has_s_corp=has_s_corp,
    pays_quarterly_estimates=pays_quarterly_estimates,
    primary_has_w2_only=primary_has_w2_only,
)

st.sidebar.markdown("---")
st.sidebar.header("Payment Resources")
st.sidebar.markdown(
    f"""
    **Pay quarterly estimated taxes:**
    
    - [Federal (IRS)](https://sa.www4.irs.gov/ola/) - Pay federal quarterly estimates
    - [{STATES_AVAILABLE[selected_state]['name']} Tax Site]({STATES_AVAILABLE[selected_state].get('tax_portal_url', 'https://www.irs.gov')}) - {STATES_AVAILABLE[selected_state]['name']} tax resources and payments
    """
)

with st.expander("1. Build or refresh legal source index", expanded=True):
    st.write(f"Indexes configured {selected_state} and Federal IRS sources for citation based answers.")
    if st.button("Build law index", type="primary"):
        with st.spinner("Downloading and indexing sources. This can take a few minutes."):
            stats = build_law_index()
        st.success(
            (
                f"Indexed roots: {stats.get('roots', 0)} | "
                f"indexed sources: {stats['sources']} | "
                f"new chunks: {stats['chunks']} | "
                f"failed sources: {stats.get('failed_sources', 0)} | "
                f"new sources: {stats.get('new_sources', 0)} | "
                f"updated sources: {stats.get('updated_sources', 0)}"
            )
        )

        changed_sources = stats.get("changed_sources", [])
        if changed_sources:
            st.subheader("Changed source citations")
            for source_url in changed_sources:
                st.write(source_url)

    recent_changes = get_recent_source_changes(limit=15)
    if recent_changes:
        st.subheader("Recent source changes")
        st.dataframe(recent_changes, use_container_width=True)

    with st.expander("View configured legal source roots", expanded=False):
        st.info(f"Showing sources for: {selected_state}")
        
        selected_root = st.selectbox(
            "Select a crawl root to view details",
            options=root_names,
            index=0,
        )
        
        selected_root_obj = roots_by_name.get(selected_root)
        if selected_root_obj:
            st.write(f"**Jurisdiction:** {selected_root_obj.jurisdiction}")
            st.write(f"**Seed URL:** {selected_root_obj.seed_url}")
            st.write(f"**Max pages:** {selected_root_obj.max_pages} | **Max depth:** {selected_root_obj.max_depth}")
            
            if selected_root_obj.additional_seed_urls:
                st.write("**Additional seed URLs:**")
                for url in selected_root_obj.additional_seed_urls:
                    st.write(f"- {url}")

with st.expander("2. Upload statements and extract possible business expenses", expanded=True):
    pdf_status = get_pdf_extraction_status()
    if pdf_status["ocr"] != "available":
        st.warning(
            "OCR for scanned PDFs is unavailable. Install Tesseract OCR or rapidocr-onnxruntime. "
            f"Current tesseract: {pdf_status['tesseract']} | rapidocr: {pdf_status.get('rapidocr', 'unknown')}"
        )
    else:
        st.caption(
            "Statement parsing ready: All tools available for PDF, CSV, and scanned document processing."
        )

    review_root_dir = Path(st.session_state.tax_review_root_dir)
    statements_upload_dir = review_root_dir / "Statements" / "uploads"
    statements_extract_dir = review_root_dir / "Statements" / "extracts"

    uploaded_files = st.file_uploader(
        "Upload statements from Costco, Amazon, Chase, Amex, Wells Fargo, Bank of America, Apple Card, etc. (PDF, CSV, or scanned images)",
        type=["pdf", "csv", "png", "jpg", "jpeg", "tif", "tiff"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        parsed: list[Transaction] = []
        for file in uploaded_files:
            destination = _save_uploaded_file(file, statements_upload_dir)
            file_txns = parse_statement(destination)
            parsed.extend(file_txns)

            if file_txns:
                per_file_df = summarize_transactions(file_txns)
                saved_path = _save_extract_csv(per_file_df, Path(file.name).stem, beside=statements_extract_dir)
                st.caption(
                    f"{file.name}: {len(file_txns)} transactions extracted "
                    f"| saved to {saved_path.relative_to(settings.project_root)}"
                )
            else:
                st.warning(
                    f"{file.name}: no transactions found. The file may be an unsupported format, "
                    "a non-transaction statement, or a password-protected PDF."
                )

        st.session_state.transactions = parsed

    if st.session_state.transactions:
        df = summarize_transactions(st.session_state.transactions)
        st.caption(
            "Negative amounts are credits, refunds, or card payments. "
            "Use expense only totals for deduction review."
        )
        expense_only_view = st.checkbox(
            "Table view: expense spending only",
            value=True,
            help="Hides negative rows such as card payments, refunds, and credits in the table view.",
        )
        display_df = df
        if expense_only_view:
            display_df = display_df[display_df["amount"] > 0]

        st.dataframe(display_df, use_container_width=True)

        if not df.empty:
            combined_path = _save_extract_csv(df, "combined", beside=statements_extract_dir)
            st.caption(f"Combined extract saved to {combined_path.relative_to(settings.project_root)}")
            st.download_button(
                label="Download combined CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="transactions_extracted.csv",
                mime="text/csv",
            )

            deductible_only_totals = st.checkbox(
                "Category totals: deductible transactions only",
                value=True,
                help="When on, totals include rows marked Deductible only.",
            )
            expense_only_totals = st.checkbox(
                "Category totals: expense spending only (exclude negatives)",
                value=True,
                help="When on, excludes negative amounts such as payments and credits.",
            )
            totals_source = (
                df[df["deductible_status"] == "Deductible"]
                if deductible_only_totals
                else df
            )
            if expense_only_totals:
                totals_source = totals_source[totals_source["amount"] > 0]
            totals = totals_source.groupby("category", dropna=False)["amount"].sum().reset_index()
            totals = totals.sort_values(by="amount", ascending=False)
            st.subheader("Category totals")
            st.dataframe(totals, use_container_width=True)
            st.download_button(
                label="Download category totals CSV",
                data=totals.to_csv(index=False).encode("utf-8"),
                file_name="category_totals.csv",
                mime="text/csv",
                key="dl_totals",
            )

with st.expander("1. Upload 1040 and supporting tax documents (Optional as this has no bearing on Deduction review brief for #4)", expanded=True):
    st.write(
        "Use this section for your final return, schedules, W2s, 1099s, brokerage forms, and any tax year support records. "
        "Files are saved into a separate review folder so the agent can analyze them independently from card statements."
    )
    st.info(
        "Recommended prompt: open docs/templates/1040-review-prompt.txt and paste it into the _Tax-Research-Assistant_Agent after upload."
    )

    review_root_dir_input = st.text_input(
        "Save the full review packet in this folder",
        value=st.session_state.tax_review_root_dir,
        help="The agent can be pointed at this same folder after extraction is done.",
        key="tax_review_root_dir",
    )
    review_root_dir = Path(review_root_dir_input)
    tax_return_upload_dir = review_root_dir / "Tax Return" / "uploads"
    tax_return_extract_dir = review_root_dir / "Tax Return" / "extracts"

    st.caption(f"Active review root: {review_root_dir}")
    st.caption(f"Tax upload folder: {tax_return_upload_dir}")
    st.caption(f"Tax extract folder: {tax_return_extract_dir}")

    tax_review_files = st.file_uploader(
        "Upload 1040, schedules, W2s, 1099s, and supporting tax docs",
        type=["pdf", "csv", "png", "jpg", "jpeg", "tif", "tiff"],
        accept_multiple_files=True,
        key="tax_review_uploads",
    )

    if tax_review_files:
        review_transactions: list[Transaction] = []
        return_summaries: list[TaxReturnSummary] = []
        line_item_frames: list[pd.DataFrame] = []
        processed_files = 0
        for file in tax_review_files:
            processed_files += 1
            destination = _save_uploaded_file(file, tax_return_upload_dir)
            file_txns = parse_statement(destination)
            review_transactions.extend(file_txns)

            return_summary = parse_tax_return_summary(destination)
            if return_summary is not None:
                return_summaries.append(return_summary)

            line_items_df = parse_tax_form_line_items(destination)
            if not line_items_df.empty:
                line_item_frames.append(line_items_df)

            if file_txns:
                per_file_df = summarize_transactions(file_txns)
                saved_path = _save_extract_csv(per_file_df, Path(file.name).stem, beside=tax_return_extract_dir)
                st.caption(
                    f"{file.name}: {len(file_txns)} extracted rows saved to {saved_path.relative_to(settings.project_root)}"
                )
            else:
                st.caption(
                    f"{file.name}: saved for review at {destination.relative_to(settings.project_root)}"
                )

            if return_summary is not None:
                st.caption(
                    f"{file.name}: {return_summary.form_type} key fields detected for filing year {return_summary.filing_year}."
                )

        st.info(
            f"Processed {processed_files} file(s). Extracted {len(review_transactions)} transaction row(s), "
            f"{len(return_summaries)} key field summary file(s), and {len(line_item_frames)} line item file(s)."
        )

        if review_transactions:
            review_df = summarize_transactions(review_transactions)
            review_path = _save_extract_csv(review_df, "tax_review_combined", beside=tax_return_extract_dir)
            st.success(
                f"Review packet created with {len(review_df)} extracted rows and saved to {review_path.relative_to(settings.project_root)}"
            )
            st.dataframe(review_df, use_container_width=True)
            st.download_button(
                label="Download tax review CSV",
                data=review_df.to_csv(index=False).encode("utf-8"),
                file_name="tax_review_combined.csv",
                mime="text/csv",
                key="dl_tax_review",
            )
        else:
            st.warning(
                "Files were saved for review, but no transaction style rows were extracted. That is normal for many forms. "
                "Use the prompt template with the _Tax-Research-Assistant_Agent to review the documents manually."
            )

        if return_summaries:
            returns_df = summarize_tax_return_summaries(return_summaries)
            coverage_rows: list[dict[str, object]] = []
            for item in return_summaries:
                extracted, expected, missing = summarize_tax_form_coverage(item)
                pct = round((extracted / expected) * 100, 1) if expected else 0.0
                coverage_rows.append(
                    {
                        "source_file": item.source_file,
                        "form_type": item.form_type,
                        "coverage_extracted": extracted,
                        "coverage_expected": expected,
                        "coverage_pct": pct,
                        "missing_fields": ", ".join(missing),
                    }
                )
            coverage_df = pd.DataFrame(coverage_rows)
            if not coverage_df.empty:
                returns_df = returns_df.merge(
                    coverage_df,
                    on=["source_file", "form_type"],
                    how="left",
                )

            overrides_path = tax_return_extract_dir / "tax_form_manual_overrides_template.csv"
            if overrides_path.exists():
                try:
                    overrides_df = pd.read_csv(overrides_path)
                    if not overrides_df.empty and {"source_file", "field_name", "override_value"}.issubset(overrides_df.columns):
                        valid_overrides = overrides_df.copy()
                        valid_overrides["override_value"] = valid_overrides["override_value"].astype(str).str.strip()
                        valid_overrides = valid_overrides[
                            valid_overrides["override_value"].ne("")
                            & valid_overrides["override_value"].ne("nan")
                        ]

                        applied_count = 0
                        for _, row in valid_overrides.iterrows():
                            source_file = str(row["source_file"])
                            field_name = str(row["field_name"])
                            raw_value = str(row["override_value"])
                            if field_name not in returns_df.columns:
                                continue

                            parsed_value: object = raw_value
                            try:
                                parsed_value = float(raw_value.replace(",", ""))
                            except Exception:
                                parsed_value = raw_value

                            mask = returns_df["source_file"].astype(str) == source_file
                            if mask.any():
                                returns_df.loc[mask, field_name] = parsed_value
                                applied_count += int(mask.sum())

                        if applied_count > 0:
                            st.info(
                                f"Applied {applied_count} manual override value(s) from {overrides_path.relative_to(settings.project_root)}"
                            )
                except Exception:
                    st.warning(
                        "Manual override file was detected but could not be applied. "
                        "Check tax_form_manual_overrides_template.csv formatting."
                    )

            returns_path = _save_extract_csv(returns_df, "tax_form_key_fields", beside=tax_return_extract_dir)
            st.success(
                f"Tax form key field summary saved to {returns_path.relative_to(settings.project_root)}"
            )
            st.subheader("Tax form key fields")
            st.dataframe(returns_df, use_container_width=True)
            st.download_button(
                label="Download tax form key fields CSV",
                data=returns_df.to_csv(index=False).encode("utf-8"),
                file_name="tax_form_key_fields_extracted.csv",
                mime="text/csv",
                key="dl_tax_form_key_fields",
            )
        else:
            st.warning(
                "No structured key field summaries were detected from these files. "
                "Use the line item extract below for manual CPA level review."
            )

        if line_item_frames:
            all_line_items_df = summarize_tax_form_line_items(line_item_frames)
            if not all_line_items_df.empty:
                line_items_path = _save_extract_csv(
                    all_line_items_df,
                    "tax_form_line_items",
                    beside=tax_return_extract_dir,
                )
                st.success(
                    f"Tax form line item extraction saved to {line_items_path.relative_to(settings.project_root)}"
                )
                st.subheader("Tax form line items")
                st.dataframe(all_line_items_df, use_container_width=True)
                st.download_button(
                    label="Download tax form line items CSV",
                    data=all_line_items_df.to_csv(index=False).encode("utf-8"),
                    file_name="tax_form_line_items_extracted.csv",
                    mime="text/csv",
                    key="dl_tax_form_line_items",
                )
        else:
            st.error(
                "No tax line items were extracted. Check scan quality and confirm the active review root path above matches your intended folder."
            )

with st.expander("4. Ask tax questions with source citations", expanded=True):
    has_openai_key = bool(settings.openai_api_key and settings.openai_api_key.strip())
    if not has_openai_key:
        st.warning(
            "OPENAI_API_KEY is required for this section. Set it in your environment or .env file, then reload the app."
        )

    default_prompt = (
        "What potentially missed deductions should I review first for my LLC and S Corp spending, "
        "and how should W2 income and quarterly tax payments be handled under federal and South Carolina law?"
    )
    question = st.text_area("Ask your question", value=default_prompt, height=130)

    if st.session_state.transactions:
        st.subheader("Deduction review brief")
        review_brief = build_review_brief(profile, st.session_state.transactions)
        st.text_area(
            "Paste this into the _Tax-Research-Assistant_Agent after upload",
            value=review_brief,
            height=260,
        )

        extracted_folder = st.session_state.tax_review_root_dir
        st.info(f"Agent folder to review: {extracted_folder}")
        review_input = ReviewInput(folder_path=extracted_folder, transactions=None)

        if st.button("Run deduction review", disabled=not has_openai_key):
            with st.spinner("Preparing deduction review from indexed legal sources."):
                review_result = answer_deduction_review(
                    None,
                    profile=profile,
                    review_input=review_input,
                )

            st.info(
                f"Review folder set to: {extracted_folder}. The agent can load extracted CSV files from this folder when you switch to it."
            )

            st.subheader("Deduction review result")
            if last_crawled_at:
                st.write(f"Legal source crawl timestamp: {last_crawled_at}")
            st.write(review_result.answer)

            st.subheader("Deduction review citations")
            if review_result.citations:
                for citation in review_result.citations:
                    st.write(citation)
            else:
                st.write("No citations available. Build the law index first.")

    if st.button("Answer question", disabled=not has_openai_key):
        with st.spinner("Preparing answer from indexed legal sources."):
            result = answer_tax_question(
                question,
                None,
                profile=profile,
                review_input=review_input if st.session_state.transactions else None,
            )

        st.subheader("Answer")
        if last_crawled_at:
            st.write(f"Legal source crawl timestamp: {last_crawled_at}")
        st.write(result.answer)

        st.subheader("Citations")
        if result.citations:
            for citation in result.citations:
                st.write(citation)
        else:
            st.write("No citations available. Build the law index first.")
