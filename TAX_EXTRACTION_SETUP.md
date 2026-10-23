# Tax PDF Extraction Setup Guide

## What You Now Have

A fully functional agent-integrated PDF extractor for tax forms. The agent can now directly extract your W2, 1099, and Form 1040 PDFs without needing the Streamlit app.

## Setup Instructions

### Quick Start: Use the Agent Directly

When you switch the agent back to agent mode and ask me to extract tax PDFs, I will use the built-in extraction tool.

**Simply ask:**
```
Extract all tax PDFs from C:\Users\jobarbar\OneDrive - Microsoft\Documents\2025_taxes
```

Or for a single file:
```
Extract this tax form: C:\Users\jobarbar\OneDrive - Microsoft\Documents\2025_taxes\form_1040.pdf
```

### Installation (Required)

The extraction tool needs the tax_agent package to be importable. Follow these steps:

1. **Navigate to the Tax-Research-Assistant folder**
   ```
   cd c:\Users\jobarbar\github\Tax-Research-Assistant
   ```

2. **Install the package in development mode**
   ```
   pip install -e .
   ```
   Or if using uv:
   ```
   uv pip install -e .
   ```

3. **Verify dependencies are installed**
   ```
   pip list | findstr "pypdf pytesseract rapidocr pandas"
   ```
   
   You should see:
   - pypdf
   - pytesseract
   - rapidocr-onnxruntime
   - pandas

### What Happens When You Ask for Extraction

1. You provide a folder path with PDFs (or a single PDF path)
2. Agent calls the extraction tool
3. Tool reads all PDFs in the folder
4. For each PDF, it:
   - Detects the form type (W2, 1099-NEC, Form 1040, etc.)
   - Extracts key financial fields (AGI, income, withholding, etc.)
   - Validates the extracted data for consistency
5. Results display in chat with:
   - Form type detected
   - Filing year
   - All extracted values
   - Any fields that couldn't be extracted

### Example Output

```
File: form_1040_2025.pdf
Form Type: Form 1040
Filing Year: 2025
AGI: $56,060
Total Income: $60,210
Total Withholding: $8,500
Refund: $500
```

### Troubleshooting

**"Module not found: tax_agent"**
- Run: `pip install -e .` in the Tax-Research-Assistant folder
- Then ask the agent again

**"File not found: C:\Users\..."**
- Double-check the exact folder path
- Use quotes if the path has spaces

**"Could not extract data from PDF"**
- The PDF might be scanned or have poor text quality
- Try running the Streamlit app for OCR enhancement: `streamlit run app.py`

### Supported Extraction

The tool extracts these fields when present:

**Form 1040:**
- Adjusted Gross Income (AGI)
- Total Income
- Deductions
- Taxable Income
- Total Tax
- Total Withholding
- Refund/Amount Owed

**W-2:**
- Wages
- Federal Income Tax Withheld
- Social Security Wages/Tax
- Medicare Wages/Tax

**1099-NEC:**
- Nonemployee Compensation
- Federal Income Tax Withheld

**1099-INT:**
- Interest Income
- Federal Income Tax Withheld

**1099-DIV:**
- Ordinary Dividends
- Qualified Dividends
- Capital Gain Distributions

### Next Steps

1. Organize all your 2025 tax PDFs in one folder (e.g., `C:\Users\jobarbar\OneDrive - Microsoft\Documents\2025_taxes`)
2. Ask the agent to extract them: "Extract all tax PDFs from [folder path]"
3. Review the extracted data in the agent response
4. Use the data for CPA prep or quarterly estimates
