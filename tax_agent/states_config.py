"""
Multi-state tax law source configuration.

This file defines crawl roots for each state. SC (South Carolina) is the default.
Users can add their own state by copying the SC structure and updating URLs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlRoot:
    """Definition of a web crawl starting point for tax law."""
    name: str
    jurisdiction: str
    seed_url: str
    additional_seed_urls: tuple[str, ...]
    allowed_prefixes: tuple[str, ...]
    max_pages: int
    max_depth: int


# ============================================================================
# SOUTH CAROLINA (SC) - DEFAULT - LOCAL INCOME TAX + STATUTE
# ============================================================================

SC_CRAWL_ROOTS = (
    CrawlRoot(
        name="South Carolina Individual Income Tax",
        jurisdiction="south_carolina",
        seed_url="https://dor.sc.gov/iit",
        additional_seed_urls=(
            "https://dor.sc.gov/tax/individual-income",
            "https://dor.sc.gov/forms-site/Forms/SC1040_2025.pdf",
            "https://dor.sc.gov/tax/individual-income/estimated-tax",
            "https://dor.sc.gov/tax/business",
            "https://dor.sc.gov/resources-site/publications/",
            "https://dor.sc.gov/tax/business/self-employed-businesses",
        ),
        allowed_prefixes=(
            "https://dor.sc.gov/iit",
            "https://dor.sc.gov/tax/individual-income",
            "https://dor.sc.gov/tax/business",
            "https://dor.sc.gov/forms-site/Forms/",
            "https://dor.sc.gov/resources-site/publications/",
        ),
        max_pages=1500,
        max_depth=7,
    ),
    CrawlRoot(
        name="South Carolina Code of Laws Title 12 Taxation",
        jurisdiction="south_carolina",
        seed_url="https://www.scstatehouse.gov/code/title12.php",
        additional_seed_urls=(
            "https://www.scstatehouse.gov/code/t12c006.php",
            "https://www.scstatehouse.gov/code/t12c054.php",
            "https://www.scstatehouse.gov/code/t12c020.php",
            "https://www.scstatehouse.gov/code/t12c036.php",
        ),
        allowed_prefixes=(
            "https://www.scstatehouse.gov/code/title12.php",
            "https://www.scstatehouse.gov/code/t12c",
            "https://www.scstatehouse.gov/code/",
        ),
        max_pages=5000,
        max_depth=10,
    ),
    CrawlRoot(
        name="IRS Tax Code Regulations and Official Guidance",
        jurisdiction="federal",
        seed_url="https://www.irs.gov/privacy-disclosure/tax-code-regulations-and-official-guidance",
        additional_seed_urls=(
            "https://www.irs.gov/businesses/small-businesses-self-employed",
            "https://www.irs.gov/businesses/small-businesses-self-employed/s-corporations",
            "https://www.irs.gov/businesses/small-businesses-self-employed/limited-liability-company-llc",
            "https://www.irs.gov/forms-pubs/about-publication-535",
            "https://www.irs.gov/forms-pubs/about-publication-334",
            "https://www.irs.gov/forms-pubs/about-publication-463",
            "https://www.irs.gov/forms-pubs/about-publication-505",
            "https://www.irs.gov/irm",
            "https://www.irs.gov/pub/irs-pdf/p535.pdf",
            "https://www.irs.gov/pub/irs-pdf/p334.pdf",
            "https://www.irs.gov/pub/irs-pdf/p463.pdf",
            "https://www.irs.gov/pub/irs-pdf/p505.pdf",
            "https://www.irs.gov/businesses/small-businesses-self-employed/business-expenses",
            "https://www.irs.gov/businesses/small-businesses-self-employed/deducting-business-expenses",
            "https://www.irs.gov/tax-professionals/tax-code-regulations-and-official-guidance/chief-counsel-advice",
            "https://www.irs.gov/forms-pubs/about-form-1040-schedule-c",
            "https://www.irs.gov/forms-pubs/form-1040-schedule-c-instructions",
            "https://www.irs.gov/tax-professionals/letter-ruling-resources",
        ),
        allowed_prefixes=(
            "https://www.irs.gov/privacy-disclosure/tax-code-regulations-and-official-guidance",
            "https://www.irs.gov/tax-professionals",
            "https://www.irs.gov/businesses/small-businesses-self-employed",
            "https://www.irs.gov/forms-pubs",
            "https://www.irs.gov/pub/irs-pdf/",
            "https://www.irs.gov/irm",
            "https://www.irs.gov/tax-professionals/letter-ruling-resources",
        ),
        max_pages=6000,
        max_depth=9,
    ),
)


# ============================================================================
# STATE CONFIGURATION MAPPING
# ============================================================================
# Default is SC only. Add new states here.

STATES_AVAILABLE = {
    "SC": {
        "name": "South Carolina",
        "crawl_roots": SC_CRAWL_ROOTS,
        "description": "SC Individual Income Tax, SC Statute, and Federal IRS guidance",
        "tax_portal_url": "https://dor.sc.gov/",
    },
    # Template for adding new states:
    # "NY": {
    #     "name": "New York",
    #     "crawl_roots": NY_CRAWL_ROOTS,  # Define NY_CRAWL_ROOTS above
    #     "description": "NY Individual Income Tax, NY Tax Law, and Federal IRS guidance",
    #     "tax_portal_url": "https://www.tax.ny.gov/",
    # },
}


def get_states_for_publication(state_codes: list[str] = None) -> dict:
    """
    Get crawl roots for specified states.
    
    Args:
        state_codes: List of state codes (e.g., ["SC", "NY"]). If None, returns default (SC only).
    
    Returns:
        Dictionary with state info and crawl roots.
    """
    if state_codes is None:
        state_codes = ["SC"]  # Default: SC only
    
    result = {}
    for code in state_codes:
        if code in STATES_AVAILABLE:
            result[code] = STATES_AVAILABLE[code]
        else:
            raise ValueError(
                f"State '{code}' not configured. Available states: {list(STATES_AVAILABLE.keys())}"
            )
    
    return result


def get_default_crawl_roots() -> tuple[CrawlRoot, ...]:
    """Get the default crawl roots (SC + Federal)."""
    return SC_CRAWL_ROOTS
