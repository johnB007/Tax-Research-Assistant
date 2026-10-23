from __future__ import annotations

from tax_agent.statement_parser import Transaction


def build_deduction_focus_terms(transactions: list[Transaction]) -> list[str]:
    categories: list[str] = []
    for tx in transactions:
        if tx.amount > 0 and tx.deductible_status == "Deductible" and tx.category not in categories:
            categories.append(tx.category)

    category_terms = {
        "Advertising and marketing": ["advertising", "marketing", "promotion"],
        "Vehicle expenses (fuel)": ["mileage", "vehicle expenses", "fuel", "parking", "toll"],
        "Vehicle expenses (maintenance)": ["vehicle maintenance", "repairs", "oil change", "tires"],
        "Vehicle expenses (insurance)": ["auto insurance", "vehicle insurance"],
        "Office and operating supplies": ["office supplies", "operating supplies", "equipment"],
        "Software and subscriptions": ["software", "subscriptions", "SaaS", "business software"],
        "Travel expenses": ["travel", "business travel", "airfare"],
        "Travel expenses (lodging)": ["lodging", "hotel", "overnight travel"],
        "Travel expenses (ground)": ["ground transportation", "rideshare", "parking", "toll"],
        "Meals and entertainment": ["meals", "meal deductions", "business meals"],
        "Home office (utilities/internet)": ["home office", "internet", "utilities"],
        "Home office (rent)": ["home office", "rent", "exclusive use"],
        "Home office (mortgage interest)": ["home office", "mortgage interest", "exclusive use"],
        "Utilities and communications": ["phone", "internet", "communications"],
        "Professional services (tax/accounting)": ["tax preparation", "accounting", "bookkeeping"],
        "Professional services (legal)": ["legal fees", "attorney", "lawyer"],
        "Professional services": ["consulting", "professional services"],
        "Equipment and supplies": ["equipment", "tools", "supplies", "depreciation"],
        "Insurance and taxes": ["insurance", "taxes", "business insurance"],
        "Education and training": ["education", "training", "professional development"],
    }

    terms: list[str] = []
    for category in categories[:8]:
        for term in category_terms.get(category, [category.lower()]):
            if term not in terms:
                terms.append(term)
    return terms


def build_profile_terms(has_llc: bool, has_s_corp: bool, primary_has_w2_only: bool) -> list[str]:
    terms = ["IRS", "South Carolina", "business deductions"]
    if has_llc:
        terms.extend(["LLC", "Schedule C"])
    if has_s_corp:
        terms.extend(["S corporation", "S corp", "reasonable compensation", "accountable plan"])
    if not primary_has_w2_only:
        terms.extend(["self employed", "trade or business"])
    return terms


def build_review_seed_queries(
    question: str,
    transactions: list[Transaction],
    has_llc: bool,
    has_s_corp: bool,
    primary_has_w2_only: bool,
    filing_year: str | None = None,
    federal_filing_status: str | None = None,
) -> list[str]:
    review_terms = [
        "missed deductions",
        "Schedule C expenses",
        "business expenses",
        "IRS Publication 535",
        "IRS Publication 463",
        "home office",
        "mileage",
        "meals",
        "software",
        "professional fees",
        "South Carolina business tax",
    ]

    queries: list[str] = [question]
    focus_terms = build_deduction_focus_terms(transactions)
    profile_terms = build_profile_terms(has_llc, has_s_corp, primary_has_w2_only)

    if focus_terms:
        queries.append(" ".join(review_terms + profile_terms + focus_terms[:10]))

    queries.append(" ".join(review_terms + profile_terms))

    if filing_year and federal_filing_status:
        queries.append(
            f"{federal_filing_status} {filing_year} federal South Carolina LLC S corporation business deductions"
        )

    seen: set[str] = set()
    unique_queries: list[str] = []
    for query in queries:
        cleaned = " ".join(query.split()).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            unique_queries.append(cleaned)
    return unique_queries
