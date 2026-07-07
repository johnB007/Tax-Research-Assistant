from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from openai import OpenAI

from tax_agent.config import get_settings
from tax_agent.law_ingest import get_index_status
from tax_agent.retrieval import RetrievedChunk, search_law
from tax_agent.statement_parser import Transaction


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


def _context_from_chunks(chunks: Iterable[RetrievedChunk]) -> str:
    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[{idx}] {chunk.source_name} | {chunk.citation_label} | {chunk.source_url}\n{chunk.content}"
        )
    return "\n\n".join(lines)


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
    transactions: list[Transaction],
    profile: FilingProfile | None = None,
) -> AgentAnswer:
    chunks = search_law(question)
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
    expense_context = _expense_context(transactions)
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
                        "You are a tax research assistant. "
                        "Use only the provided legal context and expense summary. "
                        "Use filing profile context when applying thresholds and filing year references. "
                        "Always state the legal source crawl timestamp in the response. "
                        "Explain uncertainty clearly. "
                        "Always include a short disclaimer that this is not legal or tax advice."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User question:\n{question}\n\n"
                        f"Crawl metadata:\n{crawl_context}\n\n"
                        f"Filing profile:\n{profile_context}\n\n"
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
        "Most relevant sources were retrieved. Review the citations and verify the latest filing year details directly in those sources. "
        "This tool provides research support and is not legal or tax advice."
    )
    return AgentAnswer(answer=fallback, citations=citations)
