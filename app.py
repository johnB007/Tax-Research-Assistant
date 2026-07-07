from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import json

from tax_agent.agent import FilingProfile, answer_tax_question
from tax_agent.config import get_settings
from tax_agent.law_ingest import build_law_index, get_index_status, get_recent_source_changes
from tax_agent.states_config import STATES_AVAILABLE, get_states_for_publication
from tax_agent.statement_parser import (
    Transaction,
    get_pdf_extraction_status,
    parse_statement,
    summarize_transactions,
)


def _save_extract_csv(df: pd.DataFrame, source_stem: str, beside: Path | None = None) -> Path:
    save_dir = beside.parent if beside is not None else (settings.data_dir / "extracts")
    save_dir.mkdir(parents=True, exist_ok=True)
    out_path = save_dir / f"{source_stem}_extracted.csv"
    df.to_csv(out_path, index=False)
    return out_path

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

    uploaded_files = st.file_uploader(
        "Upload statements from Costco, Amazon, Chase, Amex, Wells Fargo, Bank of America, Apple Card, etc. (PDF, CSV, or scanned images)",
        type=["pdf", "csv", "png", "jpg", "jpeg", "tif", "tiff"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        parsed: list[Transaction] = []
        for file in uploaded_files:
            destination = settings.uploads_dir / Path(file.name).name
            destination.write_bytes(file.read())
            file_txns = parse_statement(destination)
            parsed.extend(file_txns)

            if file_txns:
                per_file_df = summarize_transactions(file_txns)
                saved_path = _save_extract_csv(per_file_df, Path(file.name).stem, beside=destination)
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
        st.dataframe(df, use_container_width=True)

        if not df.empty:
            combined_path = _save_extract_csv(df, "combined", beside=destination)
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

with st.expander("3. Ask tax questions with source citations", expanded=True):
    default_prompt = (
        "What deductions might apply to LLC and S Corp spending for software, travel, and supplies, "
        "and how should W2 income and quarterly tax payments be handled?"
    )
    question = st.text_area("Ask your question", value=default_prompt, height=130)

    if st.button("Answer question"):
        with st.spinner("Preparing answer from indexed legal sources."):
            result = answer_tax_question(question, st.session_state.transactions, profile=profile)

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
