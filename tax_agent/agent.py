from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openai import OpenAI

from tax_agent.config import get_settings
from tax_agent.law_ingest import get_index_status
from tax_agent.retrieval import RetrievedChunk, search_law
from tax_agent.tax_tools import build_review_seed_queries
from tax_agent.statement_parser import Transaction, load_transactions_from_folder


@dataclass
class AgentAnswer:
    answer: str
    citations: list[str]


@dataclass
class FilingProfile:
    filing_year: str
    federal_filing_status: str
    state_residency: str
    has_llc: bool
    has_s_corp: bool
    pays_quarterly_estimates: bool
    primary_has_w2_only: bool


@dataclass
class ReviewInput:
    folder_path: str | None = None
    transactions: list[Transaction] | None = None


def _resolve_transactions(review_input: ReviewInput | None) -> tuple[list[Transaction], str]:
    if review_input is None:
        return [], "No review input was provided."

    if review_input.transactions:
        return list(review_input.transactions), "Transactions were provided directly from the app."

    if review_input.folder_path:
        folder = Path(review_input.folder_path).expanduser()
        transactions = load_transactions_from_folder(folder)
        if transactions:
            return transactions, f"Loaded {len(transactions)} transactions from folder: {folder}"
        return [], f"No extract CSV files were found in folder: {folder}"

    return [], "No extracted transaction folder was provided."


def build_review_brief(profile: FilingProfile | None, transactions: list[Transaction], source_note: str | None = None) -> str:
    lines: list[str] = []
    lines.append("Review goal: find potentially missed deductions first, then separate business, personal, and transfer activity.")
    lines.append("Focus on LLC and S Corp business owners who may have left deductible expenses on the table.")
    lines.append("Treat mixed use items carefully and flag anything that needs CPA confirmation.")
    if source_note:
        lines.append(f"Data source: {source_note}")

    if profile is not None:
        lines.append("")
        lines.append("Filing profile:")
        lines.append(f"- Filing year: {profile.filing_year}")
        lines.append(f"- Federal filing status: {profile.federal_filing_status}")
        lines.append(f"- State residency: {profile.state_residency}")
        lines.append(f"- Has LLC activity: {profile.has_llc}")
        lines.append(f"- Has S Corp activity: {profile.has_s_corp}")
        lines.append(f"- Pays quarterly estimates: {profile.pays_quarterly_estimates}")
        lines.append(f"- Primary has W2 only: {profile.primary_has_w2_only}")

    if transactions:
        totals: dict[str, float] = {}
        deductible_totals: dict[str, float] = {}
        for tx in transactions:
            totals[tx.category] = totals.get(tx.category, 0.0) + tx.amount
            if tx.deductible_status == "Deductible" and tx.amount > 0:
                deductible_totals[tx.category] = deductible_totals.get(tx.category, 0.0) + tx.amount

        lines.append("")
        lines.append("Uploaded transaction summary:")
        lines.append(f"- Total extracted rows: {len(transactions)}")
        lines.append("- Spend by category:")
        for category, amount in sorted(totals.items(), key=lambda item: item[0]):
            lines.append(f"  - {category}: ${amount:,.2f}")
        if deductible_totals:
            lines.append("- Deductible spend by category:")
            for category, amount in sorted(deductible_totals.items(), key=lambda item: item[0]):
                lines.append(f"  - {category}: ${amount:,.2f}")

        lines.append("")
        lines.append("Potential missed deduction review instructions:")
        lines.append("- Identify common missing items such as software, supplies, mileage, home office, travel, phone, internet, meals, dues, insurance, contractor payments, and professional fees.")
        lines.append("- Flag transactions that may be deductible only if they support the trade or business.")
        lines.append("- Flag payments, refunds, owner draws, transfers, and credits as non deductible or not business expenses unless clearly supported.")
        lines.append("- Separate federal treatment from South Carolina treatment when the law differs.")

    return "\n".join(lines)


def _context_from_chunks(chunks: Iterable[RetrievedChunk]) -> str:
    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[{idx}] {chunk.source_name} | {chunk.citation_label} | {chunk.source_url}\n{chunk.content}"
        )
    return "\n\n".join(lines)


def _search_law_for_review(question: str, transactions: list[Transaction], profile: FilingProfile | None) -> list[RetrievedChunk]:
    queries = build_review_seed_queries(
        question=question,
        transactions=transactions,
        has_llc=profile.has_llc if profile else False,
        has_s_corp=profile.has_s_corp if profile else False,
        primary_has_w2_only=profile.primary_has_w2_only if profile else False,
        filing_year=profile.filing_year if profile else None,
        federal_filing_status=profile.federal_filing_status if profile else None,
    )
    seen: set[tuple[str, str]] = set()
    chunks: list[RetrievedChunk] = []

    for query in queries:
        for chunk in search_law(query, limit=8):
            key = (chunk.source_url, chunk.citation_label)
            if key in seen:
                continue
            seen.add(key)
            chunks.append(chunk)
            if len(chunks) >= 12:
                return chunks

    return chunks


def _expense_context(transactions: list[Transaction]) -> str:
    if not transactions:
        return "No uploaded expense data."

    totals: dict[str, float] = {}
    for tx in transactions:
        totals[tx.category] = totals.get(tx.category, 0.0) + tx.amount

    lines = ["Expense summary by category:"]
    for category, amount in sorted(totals.items(), key=lambda x: x[0]):
        lines.append(f"{category}: ${amount:,.2f}")
    return "\n".join(lines)


def _profile_context(profile: FilingProfile | None) -> str:
    if profile is None:
        return "No filing profile was provided."

    return (
        f"Filing year: {profile.filing_year}\n"
        f"Federal filing status: {profile.federal_filing_status}\n"
        f"State residency: {profile.state_residency}\n"
        f"Primary income: {'W2 only (limited deductions)' if profile.primary_has_w2_only else 'Self-employed or mixed (Schedule C eligible)'}\n"
        f"Has LLC activity: {profile.has_llc}\n"
        f"Has S Corp activity: {profile.has_s_corp}\n"
        f"Pays quarterly estimates: {profile.pays_quarterly_estimates}"
    )


def answer_tax_question(
    question: str,
    transactions: list[Transaction] | None,
    profile: FilingProfile | None = None,
    review_input: ReviewInput | None = None,
) -> AgentAnswer:
    resolved_transactions, source_note = _resolve_transactions(review_input)
    active_transactions = transactions if transactions is not None else resolved_transactions
    chunks = _search_law_for_review(question, active_transactions, profile)
    citations = [f"{chunk.source_name} | {chunk.source_url}" for chunk in chunks]

    if not chunks:
        return AgentAnswer(
            answer=(
                "No law index results were found. Build the law index first, then ask the question again. "
                "This tool provides research support and is not legal or tax advice."
            ),
            citations=[],
        )

    settings = get_settings()
    context = _context_from_chunks(chunks)
    review_brief = build_review_brief(profile, active_transactions, source_note=source_note)
    expense_context = _expense_context(active_transactions)
    profile_context = _profile_context(profile)
    index_status = get_index_status()
    last_crawled_at = str(index_status.get("last_crawled_at", "") or "")
    crawl_context = (
        f"Last legal source crawl timestamp: {last_crawled_at}"
        if last_crawled_at
        else "Last legal source crawl timestamp: unavailable"
    )

    if settings.openai_api_key:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.model_name,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a tax deduction review assistant for LLC and S corporation owners. "
                        "Your primary job is to find potentially missed deductions, mixed use items, and CPA follow up items. "
                        "Use only the provided legal context, review brief, expense summary, and filing profile. "
                        "Use the filing profile when applying thresholds, filing year references, and entity specific rules. "
                        "Separate federal treatment from South Carolina treatment when the law differs. "
                        "Always state the legal source crawl timestamp in the response. "
                        "Explain uncertainty clearly and call out items that need records or CPA confirmation. "
                        "Always include a short disclaimer that this is not legal or tax advice."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User question:\n{question}\n\n"
                        f"Crawl metadata:\n{crawl_context}\n\n"
                        f"Filing profile:\n{profile_context}\n\n"
                        f"Deduction review brief:\n{review_brief}\n\n"
                        f"Expense context:\n{expense_context}\n\n"
                        f"Legal context:\n{context}"
                    ),
                },
            ],
        )

        text = response.output_text.strip()
        return AgentAnswer(answer=text, citations=citations)

    fallback = (
        "OpenAI API key is not configured, so this is a retrieval summary only.\n\n"
        f"Question: {question}\n\n"
        f"{crawl_context}\n\n"
        f"Filing profile:\n{profile_context}\n\n"
        f"Deduction review brief:\n{review_brief}\n\n"
        "Most relevant sources were retrieved. Review the citations and verify the latest filing year details directly in those sources. "
        "This tool provides research support and is not legal or tax advice."
    )
    return AgentAnswer(answer=fallback, citations=citations)


def answer_deduction_review(
    transactions: list[Transaction] | None,
    profile: FilingProfile | None = None,
    review_input: ReviewInput | None = None,
) -> AgentAnswer:
    question = (
        "Perform a deduction review and identify potentially missed federal and South Carolina business deductions, "
        "mixed use items, and CPA follow up questions."
    )
    return answer_tax_question(question, transactions, profile=profile, review_input=review_input)
