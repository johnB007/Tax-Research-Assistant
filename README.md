# Tax Research Assistant

**Local tax research for W2 + business household scenarios** — Statement parsing, expense categorization, and Q&A with source citations. Works offline, no cloud dependencies.

Multi-state framework ready for 50+ states. Built with Streamlit, SQLite FTS5, and Tesseract OCR.

**Status:** v1.0.0 — 116,516 indexed legal chunks from 2,742+ IRS and state tax sources.

---

## What it does

- **Statement parsing**: PDF, CSV, and scanned image uploads (Chase, Amex, Wells Fargo, Costco, Amazon, etc.)
- **Expense categorization**: 65+ IRS Schedule C rules for business deductions
- **Tax research**: Q&A with citations from indexed IRS and state law (SC + Federal included)
- **Filing profile aware**: Answers tailored to filing year, W2 income, LLC, S Corp, and quarterly payment scenarios
- **Local & private**: Run entirely offline — no cloud uploads, no telemetry
- **Multi-state ready**: Framework to add NY, TX, CA, etc. by configuration only
- **LLM optional**: Works in retrieval-only mode; OpenAI integration for answer synthesis (not required)

---

## Important: This is research only

This tool is for **education and research** only. It is **not legal, tax, or accounting advice**. Tax law changes annually. Always confirm dates, thresholds, and treatment with a licensed CPA or tax attorney before filing. Statements contain mixed transactions — final categorization requires professional review.

---

## Designed for your scenario

1. **You and spouse**: W2 income + spouse-owned LLC and S Corp
2. **Quarterly estimates**: Track and plan estimated tax payments
3. **Business spend**: Upload credit card, bank, and payment processor statements
4. **Deduction research**: Find IRS guidance on what's deductible, ordinary, and necessary
5. **Multi-year filing**: Set filing year (2026, 2025, 2024, 2023) and get year-aware answers

## What is included

1. **Legal source web crawler** - Recursive ingestion of IRS and state tax law pages with change tracking.
2. **SQLite FTS5 full-text index** - 116,516 chunks from 2,742+ sources for fast retrieval with page/section metadata.
3. **Statement parsing pipeline**:
   - PDF text extraction via pypdf and pypdfium2
   - CSV import with automatic column detection
   - Scanned document OCR via Tesseract 5.5.0 and RapidOCR ONNX
   - Fallback to image processing for graphics-only PDFs
4. **Expense classification engine** - 65+ rules for vendor and keyword matching.
5. **Streamlit web interface** - Upload statements, set filing profile, ask questions, review citations.
6. **Modular architecture** - Easy to add states, expense rules, or custom prompts.
7. **Optional LLM integration** - Generate structured answers with OpenAI (requires API key, not mandatory).
8. **Scheduled refresh capability** - Windows Task Scheduler integration for weekly index updates.
9. **Custom agent mode** - VS Code agent definition for chat-based research workflow.

## Project structure

![Tax Research Assistant project structure diagram](docs/diagrams/project-structure.svg)

```
Taxes/
├── app.py                                  # Main Streamlit interface
├── requirements.txt                        # Python dependencies (all versions pinned)
├── config.json                             # User preferences (auto-created at startup)
├── .env.example                            # OpenAI API key template
├── LICENSE                                 # MIT license with tax disclaimer
├── README.md                               # This file
│
├── tax_agent/
│   ├── __init__.py
│   ├── agent.py                           # Question answering with OpenAI integration
│   ├── config.py                          # Settings loader (env, data paths)
│   ├── expense_rules.py                   # 65+ vendor/keyword deduction rules
│   ├── law_ingest.py                      # Web crawler, chunker, SQLite indexer
│   ├── law_sources.py                     # Legal source import layer
│   ├── retrieval.py                       # SQLite FTS5 search functions
│   ├── states_config.py                   # Multi-state configuration framework
│   └── statement_parser.py                # PDF/CSV/image parsing with OCR fallback
│
├── scripts/
│   ├── refresh_law_index.py               # Python refresh runner
│   └── refresh-tax-law-index.ps1          # PowerShell Task Scheduler wrapper
│
├── data/
│   ├── law_index.db                       # SQLite FTS5 index (auto-created, 40MB+)
│   ├── law_cache/                         # Downloaded pages (auto-created)
│   │   ├── refresh_reports/               # JSON reports from refresh runs
│   │   └── sources/                       # Cached HTML pages
│   └── extracts/                          # Parsed statement CSVs (user-created)
│
├── .venv/                                 # Python virtual environment (do not commit)
├── .gitignore                             # Excludes venv, db, cache, .env
└── _tax-law-architect.agent.md            # VS Code agent definition (optional)
```

## System requirements

1. **OS**: Windows 10, Windows 11, or Windows Server 2019+
2. **Python**: 3.10 or higher (tested with 3.12.x)
3. **Disk space**: 500MB free (for SQLite index, caches, and extracted statements)
4. **Internet**: Required for initial legal source download only (crawling is one-time)
5. **Optional**: Tesseract 5.5.0 for OCR support (scanned document processing)

## Quick Start (5 minutes)

### Step 1: Clone and navigate to the project

```powershell
cd C:\Users\YourUsername\github\Taxes
```

### Step 2: Create a Python virtual environment

```powershell
python -m venv .venv
```

### Step 3: Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If you get an execution policy error, run this first:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

Then retry the activation command.

### Step 4: Install all dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- Streamlit 1.38+ (web framework)
- Pandas (data handling)
- OpenAI 1.52.2 (optional, for LLM answers)
- pypdf 4.3.0, pypdfium2 4.30.0 (PDF parsing)
- Pillow (image processing)
- pytesseract (OCR text extraction)
- rapidocr-onnxruntime (OCR fallback for scanned PDFs)
- requests, beautifulsoup4 (web crawling)
- All supporting libraries (listed in requirements.txt)

### Step 5: (Optional) Configure OpenAI API key for LLM answers

**Important**: The app works fully in retrieval-only mode without an API key. LLM-generated answers are optional.

If you want LLM answers with citations:

1. Copy the template file:
   ```powershell
   Copy-Item .env.example .env
   ```

2. Get your OpenAI API key from https://platform.openai.com/api/keys

3. Edit `.env` and paste your key:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

4. Save and close the file.

### Step 6: Start the Streamlit app

```powershell
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`

## First Time: Build the Legal Index

When you start the app for the first time, the legal index does not exist yet.

### How to build the index

1. On the app home page, expand section **1. Build or refresh legal source index**
2. Click the blue **Build law index** button
3. Wait for completion (3-8 minutes depending on internet speed)

**What happens during indexing**:
- Downloads legal pages from these roots:
  - `https://dor.sc.gov/iit` (SC Department of Revenue)
  - `https://www.scstatehouse.gov/code/title12.php` (SC Tax Code)
  - `https://www.irs.gov/privacy-disclosure/tax-code-regulations-and-official-guidance` (IRS guidance)
- Extracts text from PDFs and web pages
- Splits content into 500 character chunks with overlap
- Stores metadata (source URL, source title, crawl timestamp) in SQLite FTS5 database
- Creates full-text search index for fast retrieval
- Reports: 2,742 sources, 116,516 chunks (as of 2026-07-07)

**Success indicators**:
- Page shows: "Indexed roots: 3 | indexed sources: 2742 | new chunks: 116516"
- Recently changed sources table appears with 15+ entries
- Page refresh shows: "Legal sources last crawled: 2026-07-07 02:38:00"

**If indexing fails**:
- Check internet connectivity
- Verify no firewall blocks `dor.sc.gov`, `scstatehouse.gov`, or `irs.gov`
- Run again; the crawler resumes from last checkpoint

### View indexed sources

After indexing completes:

1. In the same section, expand **View configured legal source roots**
2. Select a source from the dropdown to see:
   - Root name (e.g., "South Carolina Individual Income Tax")
   - URL (e.g., `https://dor.sc.gov/iit`)
   - Jurisdiction and scope

## Configuring your filing profile

In the left sidebar under **Filing profile**, set these values (used in answer prompts):

### Filing year (required)

Select: 2026, 2025, 2024, or 2023

*Note*: Tax rules and thresholds change yearly. Answers are tailored to your selected year.

### Federal filing status (required)

Choose one:
- Married filing jointly (default)
- Married filing separately
- Single
- Head of household

### State residency (required)

Type your state name. Default: "South Carolina"

*Note*: This is informational for context. Legal sources are currently South Carolina and Federal only.

### Primary has W2 income only (optional)

Checkbox. Check if primary earner has only W2 wages (no business income).

### Spouse has LLC (optional)

Checkbox. Check if spouse operates a Limited Liability Company.

Default: Checked (for this household scenario)

### Spouse has S Corp (optional)

Checkbox. Check if spouse operates an S Corporation.

Default: Checked (for this household scenario)

### Quarterly estimates paid (optional)

Checkbox. Check if you make quarterly estimated tax payments.

Default: Checked

**Save automatically**: Filing profile preferences are saved to `config.json` on your local machine.

## Uploading and parsing statements

### Supported file types

- **PDF**: Text-based PDFs from banks and credit card companies
- **CSV**: Comma-separated export from Quicken, accounting software, or bank downloads
- **Images**: Scanned statements (PNG, JPG, TIFF) or PDFs with only images (no extractable text)

### Expected formats

Example data from:
- **Credit cards**: Costco, Amazon, Chase, Amex, Wells Fargo, Bank of America, Apple Card, etc.
- **Bank statements**: Checking, savings, and business accounts
- **Payment processors**: PayPal, Square, Stripe exports
- **Corporate cards**: Amex Corporate, Chase Sapphire, etc.

### Upload workflow

1. Scroll to section **2. Upload statements and extract possible business expenses**

2. Click **Choose File** button

3. Select a file from your computer (max 200MB per file)

4. Click **Upload** button

5. Wait for processing:
   - PDF text extraction: 2-5 seconds
   - CSV import: 1 second
   - Scanned image OCR: 10-30 seconds (depends on page count and image quality)

6. View results:
   - **Transaction count**: Total line items extracted
   - **Extraction methods used**: "text=available", "render=available", "ocr=available"
   - **Mapped expenses**: Count of lines categorized by rule (see Expense rules below)
   - **Low confidence**: Count of lines below categorization threshold

### Download parsed statements

After upload, results are available as CSV files in the **extracts/** folder.

Format: `{original_filename}_extracted.csv`

Columns:
- `date` - Transaction date (YYYY-MM-DD)
- `amount` - Transaction amount (positive number)
- `description` - Merchant name or transaction note
- `category` - Auto-assigned expense category (e.g., "Software", "Travel", "Supplies")
- `confidence` - Confidence score (0.0 to 1.0)
- `matched_rule` - Name of the rule that matched this transaction

## Expense categorization rules

The parser applies 65+ rules to categorize transactions. Rules match:

1. **Vendor names** (exact or substring): e.g., "Microsoft" -> "Software"
2. **Keywords in description**: e.g., "software license" -> "Software"
3. **Merchant category codes** (MCC): e.g., 5739 -> "Electronics"
4. **Amount thresholds**: Small amounts likely personal, large amounts likely business

### Common categories

- **Software & SaaS**: Microsoft, Adobe, Stripe, AWS, subscriptions
- **Travel**: Airlines, hotels, rideshare, gas/fuel
- **Meals & Entertainment**: Restaurants, coffee, catering (business meals)
- **Supplies**: Paper, ink, office equipment, shipping
- **Professional Services**: Accounting, legal, consulting
- **Rent & Utilities**: Commercial space, internet, phone
- **Insurance**: Business liability, professional
- **Advertising & Marketing**: Google Ads, Facebook, consulting

### Review and adjust

1. **Confidence scores**: Low scores (< 0.7) need manual review
2. **Unmapped items**: Transactions not matching any rule are marked "Other"
3. **False positives**: Personal expenses misclassified as business (review before claiming)

**Best practice**: Use the CSV export in your accounting software or tax preparation tool for final categorization.

## Asking tax questions with citations

### Basic workflow

1. Scroll to section **3. Ask tax questions with source citations**

2. In the text box, type your question. Examples:
   - "What deductions might apply to LLC and S Corp spending for software, travel, and supplies?"
   - "How do estimated tax payments apply to our household with W2 income and business activity?"
   - "What records should we keep for mixed personal and business expenses?"

3. Click **Answer question** button

4. Wait for response (retrieval: 2-5 seconds, LLM generation: 10-15 seconds)

### How answers are generated

#### Mode 1: Retrieval-only (no OpenAI key)

1. App searches the SQLite index for matching legal chunks
2. Returns top 5-10 results with source URLs
3. Display format: "According to [source URL], [relevant excerpt]"
4. **No LLM involved**: Purely from indexed legal text

#### Mode 2: LLM-generated with citations (OpenAI API key required)

1. App retrieves top matching legal chunks from the index
2. Sends prompt to OpenAI GPT-4 (or GPT-4o depending on account)
3. LLM synthesizes answer using filing profile context (year, status, business setup)
4. Cites sources by page URL in the response
5. Display format: "Based on [source], [answer]. See: [URL]"

**Cost**: ~$0.05-0.20 per answer (depends on question length and answer detail)

### Tips for better answers

1. **Be specific**: "Deductions for S Corp software tools" is better than "What deductions?"
2. **Include context**: Mention filing year, income type, state
3. **One topic per question**: Don't ask five questions at once
4. **Verify results**: Cross-check answers with official IRS and state resources
5. **Save important answers**: Screenshots or copy-paste for your records

### Understanding citations

Each citation includes:
- **Source title**: Page or publication name
- **Source URL**: Direct link to the referenced material
- **Retrieved date**: When the legal index crawled this source
- **Context**: If available, the chunk text that was retrieved

**Always verify online**: Visit the URL to confirm the rule hasn't changed since indexing.

## Installing OCR support for scanned statements

OCR (Optical Character Recognition) is optional but recommended if you upload scanned bank statements or invoices.

### Install Tesseract OCR on Windows

1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki

2. Run the `.exe` installer and follow the wizard:
   - Accept the license
   - Choose installation path (default: `C:\Program Files\Tesseract-OCR`)
   - Install all components

3. Verify installation by opening a new PowerShell window and typing:
   ```powershell
   tesseract --version
   ```
   
   You should see version information (e.g., `tesseract v5.3.0`).

4. If the command doesn't work:
   - Restart VS Code or PowerShell
   - Check that `tesseract.exe` is in your PATH
   - Manually add it if needed (System Properties > Environment Variables > PATH)

### Using scanned statements

After Tesseract is installed:

1. Scan your statements to PDF or JPEG/PNG images
2. Upload the file via the Streamlit app
3. The app will:
   - Try text extraction first (fastest)
   - Fall back to Tesseract OCR if no text is found
   - Fall back to RapidOCR ONNX if Tesseract fails
4. Review extracted transactions in the CSV output

**Quality tips**:
- Scan at 300 DPI or higher for best OCR accuracy
- Ensure good lighting and no skew (image is straight)
- Crop to statement area only (remove borders, headers, footers)

## Scheduling automatic index refreshes

The legal index should be refreshed periodically (weekly recommended) to capture law changes.

### Manual refresh

1. Open PowerShell in the project folder
2. Activate the virtual environment: `.\.venv\Scripts\Activate.ps1`
3. Run the refresh script: `python scripts/refresh_law_index.py`
4. Review output:
   - Console output shows progress (downloading, parsing, indexing)
   - JSON report is written to `data/law_cache/refresh_reports/{timestamp}.json`
   - Report includes: sources added, updated, failed, and new chunks

### Automatic weekly refresh with Windows Task Scheduler

#### Create the scheduled task

1. Open Windows Task Scheduler:
   - Press `Win+R`, type `taskschd.msc`, press Enter
   - Or search for "Task Scheduler" in Start menu

2. In Task Scheduler, click **Create Basic Task** (right panel)

3. Fill in the details:
   - **Name**: "Tax Research Index Refresh"
   - **Description**: "Weekly refresh of IRS and SC tax law index"
   - Click **Next**

4. **Trigger** tab:
   - Choose "Weekly"
   - Pick day: Sunday (least busy)
   - Pick time: 02:00 AM (after hours)
   - Click **Next**

5. **Action** tab:
   - Choose "Start a program"
   - **Program/script**: `pwsh` (or full path: `C:\Windows\System32\pwsh.exe`)
   - **Arguments**: 
     ```
     -NoProfile -ExecutionPolicy Bypass -File "C:\Users\jobarbar\github\Taxes\scripts\refresh-tax-law-index.ps1"
     ```
   - Click **Next**

6. **Finish** to save the task

#### Verify the task runs

1. In Task Scheduler, find your task in the list
2. Right-click and choose **Run** to test it immediately
3. Check `data/law_cache/refresh_reports/` for a new JSON file
4. Review the report for any errors

## Extending to other states

The framework is designed for multi-state expansion. To add a new state (e.g., New York):

### Step 1: Add state configuration in `tax_agent/states_config.py`

```python
NY_CRAWL_ROOTS = (
    CrawlRoot(
        name="New York Individual Income Tax",
        jurisdiction="NY",
        seed_url="https://www.tax.ny.gov/",
        additional_seed_urls=("https://www.tax.ny.gov/research/collections/",),
        allowed_prefixes=("https://www.tax.ny.gov",),
        max_pages=5000,
        max_depth=10,
    ),
    # Add more roots as needed
)

STATES_AVAILABLE["NY"] = {
    "name": "New York",
    "crawl_roots": NY_CRAWL_ROOTS,
    "description": "NY Individual Income Tax, NY Tax Law, and Federal IRS guidance",
    "tax_portal_url": "https://www.tax.ny.gov/",
}
```

### Step 2: Update `app.py` state selector

The app state selector automatically shows all entries in `STATES_AVAILABLE`. Just add the state config above and it will appear in the dropdown.

### Step 3: Rebuild the index for the new state

```powershell
# In PowerShell with venv activated
python scripts/refresh_law_index.py
```

The app will now:
- Show NY in the state selector
- Crawl and index NY tax sources
- Include NY in search results
- Display "NY Tax Site" link in Payment Resources (from `tax_portal_url`)

## Troubleshooting

### App fails to start

**Error**: `ModuleNotFoundError: No module named 'streamlit'`

**Solution**:
1. Check virtual environment is activated: `.\.venv\Scripts\Activate.ps1`
2. Reinstall dependencies: `pip install -r requirements.txt`
3. Restart the terminal

**Error**: `OPENAI_API_KEY` error on startup

**Solution**:
1. If you don't have an OpenAI key, simply remove the `.env` file (app will run in retrieval-only mode)
2. If you have a key, verify it's in `.env` in the project root folder (not elsewhere)
3. Restart the app

### Indexing fails or hangs

**Symptom**: "Build law index" button doesn't complete

**Solution**:
1. Check internet: Can you visit `dor.sc.gov` in your browser?
2. Check firewall: Verify no proxy or DPI throttling blocks legal sites
3. Restart the app and try again
4. If persistent, open an issue with the error message from the console

### PDF parsing shows "text=unavailable"

**Symptom**: Uploaded PDF has no extracted text

**Solution**:
1. If the PDF is scanned (image-only), OCR will handle it (if Tesseract is installed)
2. If it's a text PDF but parsing failed, try:
   - Opening the PDF in Adobe Reader or your PDF viewer
   - Re-exporting the PDF as a new file
   - Uploading again
3. If all PDFs fail, check Tesseract and RapidOCR installation

### OCR is slow

**Symptom**: Image upload takes > 30 seconds per page

**Solution**:
1. This is normal for first-time RapidOCR model download (~200MB, one-time)
2. Subsequent uploads will be faster
3. For better speed, increase DPI or use Tesseract instead:
   - Tesseract is often 2x faster on Windows
   - Install per "OCR setup" section above

### No search results for a question

**Symptom**: "No matching legal sources found" response

**Solution**:
1. Verify the index was built: Check "Legal sources last crawled" timestamp at top of page
2. Try simpler keywords: "LLC deductions" instead of "limited liability company business expense treatment"
3. Ask about common topics: "estimated taxes", "W2 income", "home office"
4. If blank index, click "Build law index" button

### Legal sources seem outdated

**Symptom**: You know tax law changed but index still shows old rule

**Solution**:
1. Run refresh manually: `python scripts/refresh_law_index.py`
2. Or wait for next scheduled refresh (if you set up Task Scheduler)
3. Check the JSON report to see what changed

## Custom agent mode (VS Code)

If you use VS Code Chat with GitHub Copilot or Claude:

1. Open the file `_tax-law-architect.agent.md` in VS Code
2. You may see a prompt to activate the custom agent
3. In Chat, select agent dropdown and choose "Tax Law Architect"
4. Ask tax questions in chat; answers include citations from the indexed sources

This mode uses the same retrieval and LLM pipeline as the web app but within VS Code.

## Architecture overview

```
User uploads statement or asks question
              |
              v
        Streamlit app.py
              |
     +--------+--------+
     |        |        |
     v        v        v
Statement  Expense   Q&A Agent
Parser    Classifier   |
  |          |        +----> SQLite FTS5
  |          |        |      Retrieval
  |          |        |
  CSV        CSV      +----> OpenAI API
                      |      (optional)
                      |
                      v
                   Answer with
                   citations
```

## Performance characteristics

- **App startup**: 2-3 seconds (Streamlit load + venv)
- **Statement upload (PDF text)**: 2-5 seconds
- **Statement upload (CSV)**: 1 second
- **Statement upload (scanned image)**: 10-30 seconds (OCR)
- **Search (SQLite FTS)**: 0.5-2 seconds (depends on query)
- **LLM answer generation**: 10-20 seconds (OpenAI latency)
- **Index build (full)**: 3-8 minutes (depends on internet speed)
- **Index size**: ~40-50MB for 2,742 sources and 116,516 chunks

## License and disclaimers

See `LICENSE` file for full terms.

**Summary**:
- MIT License with custom tax/legal disclaimer
- Free to use and modify for personal or commercial purposes
- No warranty; use at your own risk
- Always confirm tax treatment with a qualified CPA or attorney before filing
- This tool is for research only, not professional tax advice

## Recommended workflow for your household

1. **Setup** (one-time, 15 minutes):
   - Install Python dependencies
   - Build the legal index
   - (Optional) Install Tesseract for scanned statements

2. **Quarterly** (2-3 times per year):
   - Upload Q1, Q2, Q3, Q4 bank and credit card statements
   - Review categorized expenses
   - Note items for your CPA (mixed-use, edge cases)

3. **Before filing** (annually):
   - Reconcile all statements with CPA
   - Confirm LLC and S Corp treatment with tax professional
   - Verify quarterly estimated payments were sufficient

4. **Throughout the year**:
   - Ask specific tax questions as situations arise (home office, new expense types, etc.)
   - Save important answers and citations
   - Review new sources (weekly if scheduled refresh is set up)

## Getting help

1. **App questions**: Check the Streamlit interface for inline help tooltips
2. **Legal research**: See the "Recommended workflow" section above
3. **Issues or bugs**: Review the "Troubleshooting" section
4. **Tax treatment**: Consult a CPA or tax attorney (this tool cannot provide tax advice)

## Changelog

**v1.0.0** (2026-07-07)
- Initial release
- 116,516 legal chunks from 2,742+ IRS and SC sources
- Streamlit web interface with filing profile controls
- Statement parsing with OCR support
- 65+ expense categorization rules
- LLM answer generation with citations (optional)
- Multi-state framework ready for 50-state expansion
- Scheduled refresh via Windows Task Scheduler

---

**Last updated**: 2026-07-07
**Maintained by**: Tax Research Assistant v1.0.0
