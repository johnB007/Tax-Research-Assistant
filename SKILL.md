---
name: Tax Research Assistant
description: Research agent for tax filing analysis with 116k IRS and state law sources, filing profile tracking, OCR parsing, and Q&A interface
---

# Tax Research Assistant

Research agent for tax filing analysis with full-text search across 116,516+ indexed legal chunks from 2,742+ IRS and state tax sources. Streamlit web interface with filing profile tracking, tax statement OCR parsing, legal source browsing, and citation-backed Q&A.

## Features

- Full-text search across 116,516 legal chunks from tax sources
- Filing profile management (year, status, state, entity type)
- Tax statement upload and OCR parsing (PDF, CSV, images)
- Interactive legal source browser
- Question answering with optional OpenAI citations
- Multi-state framework for expanding coverage
- 65+ IRS Schedule C deduction classification rules

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## System Requirements

- Python 3.10 or higher
- Windows 10, 11, or Server 2019+
- 500 MB disk space
- Tesseract 5.5.0 (for OCR)

## Usage

1. Configure filing profile (year, state, entity type)
2. Upload tax statements or expense documents
3. Search legal sources or ask questions
4. View citations and sources

## Documentation

See [README.md](README.md) for detailed usage and configuration.
