---
name: Tax Research Assistant
description: Full-text legal research agent for tax filing with 116k+ IRS and state law sources, statement parsing, expense categorization, and citation-backed Q&A. Works offline, no cloud dependencies.
author: johnB007
license: MIT
homepage: https://github.com/johnB007/Tax-Research-Assistant
repository: johnB007/Tax-Research-Assistant
tags:
  - tax
  - research
  - legal
  - expense-categorization
  - tax-filing
  - ocr
categories:
  - Finance
  - Research
  - Compliance
agents:
  - claude-code
  - cursor
  - codex
  - github-copilot
  - windsurf
  - cline
  - vscode
---

# Tax Research Assistant

Full-text legal research agent for tax filing analysis and expense categorization. Query 116,516 indexed legal chunks from 2,742+ IRS and state tax sources. Upload bank statements or expense documents. Get answers with legal citations. Fully offline, no cloud dependencies, no telemetry.

## What It Does

**Tax Research**
- Full-text search across 116,516+ legal chunks from IRS.gov, state revenue departments, and tax publications
- Query by tax topic, code section, or natural language
- Results include source URL, section number, and page reference

**Statement Parsing**
- Upload bank statements (PDF, CSV) or scanned documents (images)
- Automatic text extraction and OCR for scanned statements
- Handles mixed transactions and multi-page statements

**Expense Categorization**
- 65+ IRS Schedule C deduction classification rules
- Vendor and keyword matching against tax code
- Output CSV with categorized expenses for spreadsheet import

**Filing Profile Aware**
- Tracks filing year, tax status, state, entity type (W2, LLC, S-Corp)
- Quarterly estimated tax support
- Multi-state framework for state-specific rules

## Installation

```bash
git clone https://github.com/johnB007/Tax-Research-Assistant.git
cd Tax-Research-Assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

## Quick Start

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Configure filing profile in sidebar. Upload statements or search legal sources.

## System Requirements

- Python 3.10+
- Windows 10, 11, Server 2019+, or Linux
- 500 MB disk space
- Tesseract 5.5.0 (OCR; pre-installed on Windows)

## Features

- Full-text legal research across 2,742+ tax sources
- Statement upload and OCR parsing (PDF, CSV, images)
- 65+ IRS expense categorization rules
- Filing profile management (year, status, state, entity type)
- Interactive legal source browser with citations
- Multi-state framework (SC + Federal; extensible to all 50 states)
- Optional OpenAI integration for structured answer synthesis
- Fully offline with no cloud uploads or telemetry

## Usage Workflow

1. **Configure Filing Profile** Set tax year, status, state, entity type
2. **Upload Statements** PDF, CSV, or scanned documents
3. **Parse Expenses** Auto-categorize with IRS rules
4. **Research Tax Code** Full-text search with citations
5. **Ask Questions** Get answers backed by legal sources

## Extend to Other States

Add state-specific crawl roots to `tax_agent/law_sources.py`:

```python
CrawlRoot(
    name="NY Tax Department",
    seed_url="https://www.tax.ny.gov",
    allowed_prefixes=["https://www.tax.ny.gov/"],
    max_pages=500,
    max_depth=4
)
```

Then run `scripts/refresh_law_index.py` to index new sources.

## License

MIT License. See [LICENSE](LICENSE) file.

## Disclaimer

Research and education only. Not legal, tax, or accounting advice. Tax law changes yearly. Always confirm with a licensed CPA or attorney before filing.

## Documentation

Full details: [README.md](README.md)  
Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)  
Security: [SECURITY.md](SECURITY.md)
