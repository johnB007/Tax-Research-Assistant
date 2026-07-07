# Tax Research Agent - Multi-State Publishing Guide

## Overview

Your tax research assistant app is now ready for multi-state publication. The architecture allows you to maintain your **SC + Federal** reference implementation while enabling others to easily customize it for their own states.

## Default Configuration

**Your Setup (SC - Unchanged):**
- State selector defaults to **South Carolina (SC)**
- Crawls SC Individual Income Tax sources (dor.sc.gov)
- Crawls SC Code Title 12 Taxation (scstatehouse.gov)
- Crawls IRS Federal Tax Code and guidance
- User preferences saved to `config.json`

When anyone uses the app, they see the state selector defaulting to SC. If they want to use a different state, they can either:
1. Select a pre-configured state from the dropdown
2. Add their own state configuration

## Project Structure

```
Taxes/
├── app.py                          # Streamlit UI with state selector
├── config.json                     # User state preferences (auto-created)
├── tax_agent/
│   ├── states_config.py           # State definitions & crawl roots (NEW)
│   ├── law_sources.py             # Imports from states_config (UPDATED)
│   ├── law_ingest.py              # Web crawling engine
│   ├── expense_rules.py            # IRS Schedule C categories (65+ rules)
│   ├── statement_parser.py         # PDF/CSV parsing with OCR fallback
│   ├── agent.py                    # Tax Q&A agent
│   └── config.py                   # App settings
└── test_expense_categorization.py  # Validation suite (100% pass rate)
```

## How to Add New States

### For Forkers: Adding Your State

1. **Edit `tax_agent/states_config.py`:**

```python
# Add your state's crawl root (copy SC structure and update URLs)

NY_CRAWL_ROOTS = (
    CrawlRoot(
        name="New York Individual Income Tax",
        jurisdiction="new_york",
        seed_url="https://www.tax.ny.gov/individuals",
        additional_seed_urls=(
            "https://www.tax.ny.gov/individuals/income",
            "https://www.tax.ny.gov/forms",
            # ... add more NY-specific URLs
        ),
        allowed_prefixes=(
            "https://www.tax.ny.gov/individuals",
            "https://www.tax.ny.gov/forms",
            # ... add domain prefixes to crawl
        ),
        max_pages=1500,
        max_depth=7,
    ),
    # Add NY statute and IRS roots...
)

# Register in STATES_AVAILABLE
STATES_AVAILABLE = {
    "SC": {...},
    "NY": {
        "name": "New York",
        "crawl_roots": NY_CRAWL_ROOTS,
        "description": "NY Income Tax, NY Tax Law, and Federal IRS guidance",
    },
}
```

2. **That's it!** The app will automatically:
   - Add "NY" to the state selector dropdown
   - Load NY crawl roots when selected
   - Save user preference to `config.json`
   - Display NY-specific sources in the UI

### State Definition Template

```python
STATE_CRAWL_ROOTS = (
    CrawlRoot(
        name="Your State Income Tax",
        jurisdiction="your_state",
        seed_url="https://example.com/tax",
        additional_seed_urls=(
            "https://example.com/...",
        ),
        allowed_prefixes=(
            "https://example.com/",
        ),
        max_pages=1500,      # Adjust based on site size
        max_depth=7,         # Adjust crawl depth
    ),
    # Add state statute...
    # Add IRS federal roots (can reuse SC's IRS roots)
)
```

## Configuration Files

### `config.json` (Auto-created on first run)

```json
{
  "selected_states": ["SC"],
  "filing_year": 2026,
  "app_version": "1.0.0",
  "last_updated": "2026-07-07"
}
```

**How it works:**
- Saved automatically when user selects a state
- Persists across app restarts
- Each user has their own `config.json`

## File Changes Summary

| File | Change | Why |
|------|--------|-----|
| `tax_agent/states_config.py` | NEW | Defines CrawlRoot class and state configurations |
| `tax_agent/law_sources.py` | UPDATED | Imports from states_config, adds `get_crawl_roots_for_state()` |
| `tax_agent/law_ingest.py` | UPDATED | Imports CrawlRoot from states_config instead of law_sources |
| `app.py` | UPDATED | Adds state selector, dynamic crawl root loading, config persistence |
| `config.json` | NEW | Stores user state preferences (gitignored) |
| `expense_rules.py` | ENHANCED | 65+ IRS Schedule C rules (OpenAccountant taxonomy) |

## Running the App

### First Time (SC Default)

```bash
cd Taxes
python -m streamlit run app.py
```

Opens at `http://localhost:8501` with SC selected.

### Selecting a Different State

1. Use sidebar dropdown: **"Select your state"**
2. Choose from available states
3. Click through to save preference
4. Refresh app to load new sources
5. Run **"Build law index"** to crawl new state sources

## Publishing to GitHub

### Your Reference Implementation (SC)

```bash
git init
git add .
git commit -m "Tax Research Agent - SC reference implementation with OpenAccountant categorization"
git remote add origin https://github.com/yourusername/tax-research-agent.git
git push -u origin main
```

### README for Forkers

```markdown
# Tax Research Agent

Multi-state tax research tool with expense categorization.

## Quick Start

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `streamlit run app.py`
4. Select your state from sidebar

## Customize for Your State

See [Adding New States](docs/ADDING_STATES.md) for step-by-step instructions.

## Features

- PDF/CSV statement parsing with OCR fallback (RapidOCR)
- 65+ IRS Schedule C expense categories
- Multi-state tax source indexing
- AI-powered tax Q&A with citations
- Filing profile context (W2-only vs self-employed)

## Default Configuration

Comes with **South Carolina + Federal IRS** sources configured.
```

## Testing Before Publishing

Run the test suite:

```bash
python test_expense_categorization.py
```

**Expected Output:**
```
Total Tests:     44
Passed:          44
Failed:          0
Pass Rate:       100.0%
```

## What Stays In Your SC Build

✓ SC Individual Income Tax crawl root  
✓ SC Code Title 12 Taxation root  
✓ IRS Federal Tax Code root  
✓ Filing profile with W2 checkbox  
✓ 65+ expense categorization rules  
✓ PDF parsing with RapidOCR fallback  
✓ All app functionality  

**Nothing changes in your SC setup** - the multi-state framework is transparent to your default experience.

## What Others Can Customize

- Add new states to `states_config.py`
- Modify crawl parameters (max_pages, max_depth)
- Add more expense categories to `expense_rules.py`
- Change filing profile fields in `agent.py`
- Deploy to their own Streamlit Cloud or server

## Technology Stack

- **Streamlit** 1.38+ - Web UI
- **Python 3.12+** - Runtime
- **SQLite + FTS5** - Law indexing
- **RapidOCR** 1.2.3 - PDF OCR (no system binary required)
- **OpenAI** 1.52.2 - Question answering
- **pandas** - Data manipulation
- **Beautiful Soup** - Web scraping

## Support for Forkers

New users adding states should:
1. Find their state's DOR/tax authority website
2. Extract main URLs (income tax, forms, statute)
3. Add to `states_config.py` following the SC template
4. Test crawling with small `max_pages` values first
5. Run law index build to populate sources

## Version Info

- **App Version:** 1.0.0
- **Expense Rules:** OpenAccountant-aligned (65+ categories, 100% test pass rate)
- **Legal Sources:** SC (1500 pages, depth 7) + SC Statute (5000 pages, depth 10) + IRS (6000 pages, depth 9)
- **Publication Date:** 2026-07-07

---

**Ready to publish!** Your SC build is the reference implementation, but the architecture is extensible for any state.
