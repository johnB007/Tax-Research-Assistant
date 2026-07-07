"""
Tax law source crawl roots.

Imports from states_config to support multi-state setup.
Default is SC (South Carolina) + Federal IRS.
Users can extend states_config.py to add new states.
"""

from tax_agent.states_config import CrawlRoot, SC_CRAWL_ROOTS

# Default crawl roots: SC + Federal
LAW_CRAWL_ROOTS: list[CrawlRoot] = list(SC_CRAWL_ROOTS)


def get_crawl_roots_for_state(state_code: str) -> list[CrawlRoot]:
    """
    Get crawl roots for the specified state.
    
    Args:
        state_code: State code (e.g., "SC", "NY"). Defaults to "SC" if not found.
    
    Returns:
        List of CrawlRoot objects for that state.
    """
    from tax_agent.states_config import STATES_AVAILABLE
    
    if state_code not in STATES_AVAILABLE:
        state_code = "SC"  # Fallback to SC
    
    state_config = STATES_AVAILABLE[state_code]
    return list(state_config["crawl_roots"])


__all__ = ["LAW_CRAWL_ROOTS", "get_crawl_roots_for_state", "CrawlRoot"]
