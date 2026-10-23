from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

try:
    import numpy as np
except Exception:
    np = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    import pypdfium2 as pdfium
except Exception:
    pdfium = None

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    RapidOCR = None

from tax_agent.expense_rules import assess_deductibility, classify_expense


@dataclass
class Transaction:
    source_file: str
    date: str
    description: str
    amount: float
    category: str
    confidence: float
    note: str
    deductible_status: str
    deductible_note: str


@dataclass
class TaxReturnSummary:
    source_file: str
    form_type: str
    filing_year: str
    total_income: float | None
    adjusted_gross_income: float | None
    deductions: float | None
    qualified_business_income_deduction: float | None
    taxable_income: float | None
    total_credits: float | None
    total_withholding: float | None
    estimated_tax_payments: float | None
    total_payments: float | None
    refund: float | None
    amount_you_owe: float | None
    total_tax: float | None
    wages: float | None
    federal_income_tax_withheld: float | None
    social_security_wages: float | None
    social_security_tax_withheld: float | None
    medicare_wages_and_tips: float | None
    medicare_tax_withheld: float | None
    nonemployee_compensation: float | None
    interest_income: float | None
    ordinary_dividends: float | None
    qualified_dividends: float | None
    capital_gain_distributions: float | None
    business_income_or_loss: float | None
    gross_receipts_or_sales: float | None
    total_expenses: float | None
    additional_income: float | None
    adjustments_to_income: float | None


DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"^(\d{1,2}/\d{2})\b"),  # Chase: MM/DD at line start
]

AMOUNT_PATTERN = re.compile(r"(-?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$")
_RAPID_OCR_ENGINE: object | None = None
_MIN_LAYOUT_CHARS_PER_PAGE = 100
_MIN_TOTAL_TEXT_CHARS = 300


def _resolve_tesseract_command() -> str | None:
    if pytesseract is None:
        return None

    detected = shutil.which("tesseract")
    if detected:
        pytesseract.pytesseract.tesseract_cmd = detected
        return detected

    common_paths = [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ]
    for candidate in common_paths:
        if candidate.exists():
            pytesseract.pytesseract.tesseract_cmd = str(candidate)
            return str(candidate)

    return None


def get_pdf_extraction_status() -> dict[str, str]:
    tesseract_cmd = _resolve_tesseract_command()
    rapidocr_ready = "available" if RapidOCR is not None else "unavailable"
    ocr_ready = (
        Image is not None
        and (
            (pytesseract is not None and tesseract_cmd is not None)
            or rapidocr_ready == "available"
        )
    )
    return {
        "pdf_text": "available" if PdfReader is not None else "unavailable",
        "pdf_render": "available" if pdfium is not None else "unavailable",
        "ocr": "available" if ocr_ready else "unavailable",
        "tesseract": tesseract_cmd or "not_found",
        "rapidocr": rapidocr_ready,
    }


def _rapid_ocr_text(image_content: object) -> str:
    global _RAPID_OCR_ENGINE

    if RapidOCR is None:
        return ""

    try:
        if _RAPID_OCR_ENGINE is None:
            _RAPID_OCR_ENGINE = RapidOCR()
        result, _ = _RAPID_OCR_ENGINE(image_content)
    except Exception:
        return ""

    if not result:
        return ""

    lines: list[str] = []
    for item in result:
        if isinstance(item, (list, tuple)) and len(item) >= 2 and isinstance(item[1], str):
            value = item[1].strip()
            if value:
                lines.append(value)

    return "\n".join(lines)


def _transactions_from_text(source_file: str, text: str) -> list[Transaction]:
    transactions: list[Transaction] = []
    source_stem = Path(source_file).stem
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        date_match = None
        for pattern in DATE_PATTERNS:
            date_match = pattern.search(line)
            if date_match:
                break
        if not date_match:
            continue

        amount_match = AMOUNT_PATTERN.search(line)
        if not amount_match:
            continue

        date_value = _normalize_date(date_match.group(1), source_stem)
        amount_value = _parse_amount(amount_match.group(1))
        if amount_value is None:
            continue

        description = line[date_match.end() : amount_match.start()].strip(" -")
        if not description:
            continue

        category, confidence, note = classify_expense(description)
        deductible_status, deductible_note = assess_deductibility(category, description)
        transactions.append(
            Transaction(
                source_file=source_file,
                date=date_value,
                description=description,
                amount=amount_value,
                category=category,
                confidence=confidence,
                note=note,
                deductible_status=deductible_status,
                deductible_note=deductible_note,
            )
        )
    return transactions


def _ocr_image_to_text(image_path: Path) -> str:
    if Image is None:
        return ""

    try:
        with Image.open(image_path) as image:
            if pytesseract is not None and _resolve_tesseract_command() is not None:
                return pytesseract.image_to_string(image, config="--psm 6")
            if np is not None:
                return _rapid_ocr_text(np.array(image))
            return _rapid_ocr_text(image_path)
    except Exception:
        return ""


def _ocr_pdf_page_texts(file_path: Path) -> list[str]:
    if pdfium is None or Image is None:
        return []

    texts: list[str] = []
    has_tesseract = pytesseract is not None and _resolve_tesseract_command() is not None
    has_rapid = RapidOCR is not None
    if not has_tesseract and not has_rapid:
        return []

    try:
        document = pdfium.PdfDocument(str(file_path))
        for index in range(len(document)):
            page = document[index]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            if has_tesseract:
                text = pytesseract.image_to_string(pil_image, config="--psm 6")
            elif np is not None:
                text = _rapid_ocr_text(np.array(pil_image))
            else:
                text = ""
            if text.strip():
                texts.append(text)
    except Exception:
        return []

    return texts


def _normalize_date(text: str, source_file_stem: str = "") -> str:
    text = text.strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Chase short date MM/DD: infer year from filename like 20260112 -> 2026-01
    m = re.match(r"^(\d{1,2})/(\d{2})$", text)
    if m:
        year = source_file_stem[:4] if len(source_file_stem) >= 4 and source_file_stem[:4].isdigit() else str(datetime.now().year)
        mo, day = m.group(1).zfill(2), m.group(2)
        try:
            return datetime.strptime(f"{year}-{mo}-{day}", "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            pass
    return text


def _parse_amount(text: str) -> float | None:
    clean = text.replace("$", "").replace(",", "").strip()
    is_negative = False
    if clean.startswith("(") and clean.endswith(")"):
        is_negative = True
        clean = clean[1:-1].strip()
    if clean.endswith("-"):
        is_negative = True
        clean = clean[:-1].strip()
    try:
        value = float(clean)
        return -value if is_negative else value
    except ValueError:
        return None


def _extract_pdf_text_blocks(file_path: Path, max_pages: int | None = None, ocr_fallback: bool = True) -> list[str]:
    blocks: list[str] = []
    total_chars = 0

    try:
        reader = PdfReader(str(file_path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                reader = None

        if reader is not None:
            page_count = len(reader.pages)
            pages_to_process = min(max_pages or page_count, page_count)
            for page_index in range(pages_to_process):
                page = reader.pages[page_index]
                try:
                    text = page.extract_text(extraction_mode="layout") or ""
                    if len(text.strip()) < _MIN_LAYOUT_CHARS_PER_PAGE:
                        text = page.extract_text() or ""
                except Exception:
                    text = ""
                if text.strip():
                    blocks.append(text)
                    total_chars += len(text.strip())
    except Exception:
        blocks = []

    if ocr_fallback and (not blocks or total_chars < _MIN_TOTAL_TEXT_CHARS):
        ocr_blocks = _ocr_pdf_page_texts(file_path)
        if ocr_blocks:
            if not blocks:
                blocks.extend(ocr_blocks)
            else:
                # Keep direct extraction first, then append OCR text when extracted text is weak.
                blocks.extend(ocr_blocks)

    return blocks


def parse_csv_statement(file_path: Path) -> list[Transaction]:
    df = pd.read_csv(file_path)
    columns = {c.lower().strip(): c for c in df.columns}

    date_col = next((columns[k] for k in columns if "date" in k), None)
    desc_col = next((columns[k] for k in columns if "description" in k or "merchant" in k), None)
    amount_col = next((columns[k] for k in columns if "amount" in k), None)

    if not date_col or not desc_col or not amount_col:
        return []

    transactions: list[Transaction] = []
    for _, row in df.iterrows():
        date = _normalize_date(str(row[date_col]))
        description = str(row[desc_col]).strip()
        amount = _parse_amount(str(row[amount_col]))
        if not description or amount is None:
            continue
        category, confidence, note = classify_expense(description)
        deductible_status, deductible_note = assess_deductibility(category, description)
        transactions.append(
            Transaction(
                source_file=file_path.name,
                date=date,
                description=description,
                amount=amount,
                category=category,
                confidence=confidence,
                note=note,
                deductible_status=deductible_status,
                deductible_note=deductible_note,
            )
        )

    return transactions


def parse_pdf_statement(file_path: Path) -> list[Transaction]:
    transactions: list[Transaction] = []
    for text in _extract_pdf_text_blocks(file_path):
        transactions.extend(_transactions_from_text(file_path.name, text))

    return transactions


def parse_image_statement(file_path: Path) -> list[Transaction]:
    text = _ocr_image_to_text(file_path)
    if not text.strip():
        return []
    return _transactions_from_text(file_path.name, text)


def parse_statement(file_path: Path) -> list[Transaction]:
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return parse_csv_statement(file_path)
    if suffix == ".pdf":
        return parse_pdf_statement(file_path)
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        return parse_image_statement(file_path)
    return []


_CORE_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "total_income": ("total income",),
    "adjusted_gross_income": ("adjusted gross income", "agi"),
    "deductions": ("deductions", "standard deduction", "itemized deductions"),
    "qualified_business_income_deduction": (
        "qualified business income deduction",
        "qualified business income",
    ),
    "taxable_income": ("taxable income",),
    "total_credits": ("total credits",),
    "total_withholding": ("federal income tax withheld", "withholding"),
    "estimated_tax_payments": ("estimated tax payments",),
    "total_payments": ("total payments",),
    "refund": ("refund",),
    "amount_you_owe": ("amount you owe", "amount owed", "tax due"),
    "total_tax": ("total tax",),
}


_FORM_FIELD_LABELS: dict[str, dict[str, tuple[str, ...]]] = {
    "Form 1040": _CORE_FIELD_LABELS,
    "Schedule 1": {
        "additional_income": ("additional income", "total additional income"),
        "adjustments_to_income": ("adjustments to income", "total adjustments to income"),
    },
    "Schedule C": {
        "gross_receipts_or_sales": ("gross receipts or sales", "gross receipts", "gross income"),
        "total_expenses": ("total expenses",),
        "business_income_or_loss": ("net profit", "net loss", "tentative profit", "profit or loss"),
    },
    "Form W-2": {
        "wages": ("wages, tips, other compensation", "box 1"),
        "federal_income_tax_withheld": ("federal income tax withheld", "box 2"),
        "social_security_wages": ("social security wages", "box 3"),
        "social_security_tax_withheld": ("social security tax withheld", "box 4"),
        "medicare_wages_and_tips": ("medicare wages and tips", "box 5"),
        "medicare_tax_withheld": ("medicare tax withheld", "box 6"),
    },
    "Form 1099-NEC": {
        "nonemployee_compensation": ("nonemployee compensation", "box 1"),
    },
    "Form 1099-MISC": {
        "nonemployee_compensation": ("other income", "rents", "royalties"),
    },
    "Form 1099-INT": {
        "interest_income": ("interest income",),
    },
    "Form 1099-DIV": {
        "ordinary_dividends": ("ordinary dividends",),
        "qualified_dividends": ("qualified dividends",),
        "capital_gain_distributions": ("total capital gain distributions", "capital gain distributions"),
    },
}


def _detect_form_type(text: str, source_file: str = "") -> str:
    lowered = text.lower()
    file_lower = source_file.lower()

    # Filename cues are usually high confidence for tax packets.
    if "w2" in file_lower or "w-2" in file_lower:
        return "Form W-2"
    if "1099-nec" in file_lower or "1099 nec" in file_lower:
        return "Form 1099-NEC"
    if "1099-int" in file_lower or "1099int" in file_lower:
        return "Form 1099-INT"
    if "1099-div" in file_lower or "1099div" in file_lower:
        return "Form 1099-DIV"
    if "1099-misc" in file_lower or "1099misc" in file_lower:
        return "Form 1099-MISC"
    if "1095-c" in file_lower or "1095c" in file_lower:
        return "Form 1095-C"
    if "form 1098" in file_lower or "1098" in file_lower:
        return "Form 1098"
    if "donation receipt" in file_lower or "charitable" in file_lower:
        return "Donation Receipt"
    if "archivetaxreturn" in file_lower or " tax return" in file_lower:
        return "Form 1040"

    # Text based detection with precedence for source forms over references.
    if "form w-2" in lowered or "wage and tax statement" in lowered:
        return "Form W-2"
    if "form 1099-nec" in lowered:
        return "Form 1099-NEC"
    if "form 1099-int" in lowered:
        return "Form 1099-INT"
    if "form 1099-div" in lowered:
        return "Form 1099-DIV"
    if "form 1099-misc" in lowered:
        return "Form 1099-MISC"
    if "form 1095-c" in lowered:
        return "Form 1095-C"
    if "form 1098" in lowered or "mortgage interest statement" in lowered:
        return "Form 1098"
    if "donation receipt" in lowered or "charitable contribution" in lowered:
        return "Donation Receipt"

    if "form 1040" in lowered or "u.s. individual income tax return" in lowered:
        return "Form 1040"
    if "schedule c" in lowered and "profit or loss from business" in lowered:
        return "Schedule C"
    if "schedule 1" in lowered and "additional income" in lowered:
        return "Schedule 1"
    return "Unknown tax form"


def _extract_form_values(text: str, form_type: str) -> dict[str, float | None]:
    values: dict[str, float | None] = {
        "total_income": None,
        "adjusted_gross_income": None,
        "deductions": None,
        "qualified_business_income_deduction": None,
        "taxable_income": None,
        "total_credits": None,
        "total_withholding": None,
        "estimated_tax_payments": None,
        "total_payments": None,
        "refund": None,
        "amount_you_owe": None,
        "total_tax": None,
        "wages": None,
        "federal_income_tax_withheld": None,
        "social_security_wages": None,
        "social_security_tax_withheld": None,
        "medicare_wages_and_tips": None,
        "medicare_tax_withheld": None,
        "nonemployee_compensation": None,
        "interest_income": None,
        "ordinary_dividends": None,
        "qualified_dividends": None,
        "capital_gain_distributions": None,
        "business_income_or_loss": None,
        "gross_receipts_or_sales": None,
        "total_expenses": None,
        "additional_income": None,
        "adjustments_to_income": None,
    }

    # Core fields map to return style documents, not wage statements.
    if form_type in {"Schedule 1", "Schedule C", "Unknown tax form"}:
        for field_name, labels in _CORE_FIELD_LABELS.items():
            values[field_name] = _extract_field_value(text, labels)

    if form_type == "Form 1098":
        values["deductions"] = _extract_field_value(
            text,
            ("mortgage interest", "mortgage insurance premiums", "points paid", "real estate taxes"),
        )

    if form_type == "Donation Receipt":
        values["deductions"] = _extract_field_value(
            text,
            ("total donation", "total contributions", "donation amount", "contribution amount", "total"),
        )

    if form_type == "Form 1040":
        line_map: dict[str, int] = {
            "total_income": 9,
            "adjusted_gross_income": 11,
            "deductions": 12,
            "qualified_business_income_deduction": 13,
            "taxable_income": 15,
            "total_tax": 24,
            "total_withholding": 25,
            "estimated_tax_payments": 26,
            "total_payments": 33,
            "refund": 34,
            "amount_you_owe": 37,
        }
        line_keywords: dict[str, tuple[str, ...]] = {
            "total_income": ("total income",),
            "adjusted_gross_income": ("adjusted gross income", "agi"),
            "deductions": ("deduction", "standard deduction", "itemized"),
            "qualified_business_income_deduction": ("qualified business income",),
            "taxable_income": ("taxable income",),
            "total_tax": ("total tax",),
            "total_withholding": ("withheld", "withholding", "federal income tax"),
            "estimated_tax_payments": ("estimated tax payments",),
            "total_payments": ("total payments",),
            "refund": ("refund",),
            "amount_you_owe": ("amount you owe", "owe"),
        }
        min_value_by_field: dict[str, float] = {
            "total_income": 100.0,
            "adjusted_gross_income": 100.0,
            "deductions": 100.0,
            "qualified_business_income_deduction": 100.0,
            "taxable_income": 100.0,
            "total_tax": 100.0,
            "total_withholding": 100.0,
            "estimated_tax_payments": 100.0,
            "total_payments": 100.0,
            "refund": 100.0,
            "amount_you_owe": 100.0,
        }
        for field_name, line_number in line_map.items():
            line_value = _extract_1040_line_value(
                text,
                line_number,
                required_keywords=line_keywords.get(field_name),
            )
            if line_value is not None:
                min_required = min_value_by_field.get(field_name, 0.0)
                if abs(line_value) >= min_required:
                    values[field_name] = line_value
                else:
                    values[field_name] = None

        for field_name, labels in _CORE_FIELD_LABELS.items():
            if values.get(field_name) is not None:
                continue
            min_required = min_value_by_field.get(field_name, 0.0)
            fallback_value = _extract_field_value_strict(text, labels, min_required)
            if fallback_value is not None:
                values[field_name] = fallback_value

        # A return cannot have both a refund and a balance due at the same time.
        refund_value = values.get("refund")
        owe_value = values.get("amount_you_owe")
        if refund_value is not None and owe_value is not None:
            if abs(refund_value) >= abs(owe_value):
                values["amount_you_owe"] = None
            else:
                values["refund"] = None

        if values["total_withholding"] is not None:
            values["federal_income_tax_withheld"] = values["total_withholding"]

    # Then apply form specific mappings.
    if form_type != "Form 1040":
        field_map = _FORM_FIELD_LABELS.get(form_type, {})
        for field_name, labels in field_map.items():
            values[field_name] = _extract_field_value(text, labels)

    if form_type == "Form W-2":
        w2_fields = [
            "wages",
            "federal_income_tax_withheld",
            "social_security_wages",
            "social_security_tax_withheld",
            "medicare_wages_and_tips",
            "medicare_tax_withheld",
        ]
        for field_name in w2_fields:
            value = values[field_name]
            if value is None:
                continue
            if _is_suspicious_tax_value(value) or abs(value) < 100:
                values[field_name] = None

    core_fields = [
        "total_income",
        "adjusted_gross_income",
        "deductions",
        "taxable_income",
        "total_tax",
        "total_payments",
        "refund",
        "amount_you_owe",
    ]
    for field_name in core_fields:
        value = values[field_name]
        if value is None:
            continue
        if _is_suspicious_tax_value(value):
            values[field_name] = None

    return values


def _is_suspicious_tax_value(value: float) -> bool:
    suspicious_values = {
        1040.0,
        1041.0,
        1065.0,
        1099.0,
        1120.0,
        2441.0,
        5695.0,
        8919.0,
        8995.0,
        2024.0,
        2025.0,
        2026.0,
    }
    return abs(value) in suspicious_values


def _extract_filing_year(text: str, source_file: str) -> str:
    name_match = re.search(r"(?<!\d)(20\d{2})(?!\d)", source_file)
    if name_match:
        return name_match.group(1)

    text_match = re.search(r"(?i)tax\s+year\s+(20\d{2})", text)
    if text_match:
        return text_match.group(1)

    fallback = re.search(r"(?<!\d)(20\d{2})(?!\d)", text)
    return fallback.group(1) if fallback else "unknown"


def _extract_field_value(text: str, labels: tuple[str, ...]) -> float | None:
    amount_token = re.compile(r"\(?\$?\d[\d,]*(?:\.\d{2})?\)?-?")

    def _pick_token(line: str) -> tuple[int, int, float] | None:
        candidates: list[tuple[int, int, float]] = []
        for idx, token in enumerate(amount_token.findall(line)):
            value = _parse_amount(token)
            if value is None:
                continue

            score = 0
            if "$" in token or "," in token or "." in token:
                score += 3
            if abs(value) >= 100:
                score += 2
            elif abs(value) >= 10:
                score += 1
            if abs(value) <= 9 and "$" not in token and "," not in token and "." not in token:
                score -= 2

            candidates.append((score, idx, value))

        if not candidates:
            return None

        best = sorted(candidates, key=lambda x: (x[0], x[1]), reverse=True)[0]
        if best[0] <= 0:
            return None
        return best

    best_overall: tuple[int, int, float] | None = None

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        lowered = line.lower()
        if not any(label in lowered for label in labels):
            continue

        candidate = _pick_token(line)
        if candidate is None:
            continue
        if best_overall is None or (candidate[0], candidate[1]) > (best_overall[0], best_overall[1]):
            best_overall = candidate

    if best_overall is not None:
        return best_overall[2]

    return None


def _extract_field_value_strict(text: str, labels: tuple[str, ...], min_required: float) -> float | None:
    amount_token = re.compile(r"\(?\$?\d[\d,]*(?:\.\d{2})?\)?-?")
    best_value: float | None = None
    best_score = -10

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        lowered = line.lower()
        if not any(label in lowered for label in labels):
            continue

        for idx, token in enumerate(amount_token.findall(line)):
            value = _parse_amount(token)
            if value is None:
                continue
            if _is_suspicious_tax_value(value):
                continue
            if abs(value) < min_required:
                continue

            score = 0
            if "$" in token or "," in token or "." in token:
                score += 3
            if abs(value) >= 1000:
                score += 2
            elif abs(value) >= 100:
                score += 1
            score += min(idx, 3)

            if score > best_score:
                best_score = score
                best_value = value

    return best_value


def _normalize_ocr_amount_runs(text: str) -> str:
    # OCR often concatenates adjacent currency tokens like 2,115.00161.80.
    return re.sub(r"(?<=\.\d{2})(?=\d)", " ", text)


def _parse_amount_relaxed(text: str) -> float | None:
    # OCR can prepend stray letters to a number token, for example R774.60.
    cleaned = re.sub(r"^[A-Za-z]+", "", text.strip())
    return _parse_amount(cleaned)


def _extract_w2_values(text: str) -> dict[str, float | None]:
    normalized = _normalize_ocr_amount_runs(text)
    amount_re = re.compile(r"[A-Za-z]?\d[\d,]*\.\d{2}")
    result: dict[str, float | None] = {
        "wages": None,
        "federal_income_tax_withheld": None,
        "social_security_wages": None,
        "social_security_tax_withheld": None,
        "medicare_wages_and_tips": None,
        "medicare_tax_withheld": None,
    }

    candidate_lines: list[str] = []
    for raw_line in normalized.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        low = line.lower()
        if "wages" in low and ("federal" in low or "reported" in low or "w-2" in low):
            candidate_lines.append(line)

    for line in candidate_lines:
        tokens = amount_re.findall(line)
        values = [_parse_amount_relaxed(token) for token in tokens]
        values = [v for v in values if v is not None and v > 0]
        if len(values) >= 2:
            wages = max(values)
            withheld = min(values)
            if wages >= 100:
                result["wages"] = wages
            if withheld >= 1:
                result["federal_income_tax_withheld"] = withheld
            break

    if result["wages"] is None or result["federal_income_tax_withheld"] is None:
        pair_pattern = re.compile(
            r"wages[^\dA-Za-z]{0,40}([A-Za-z]?\d[\d,]*\.\d{2})[^\dA-Za-z]{0,25}([A-Za-z]?\d[\d,]*\.\d{2})",
            re.IGNORECASE,
        )
        for match in pair_pattern.finditer(normalized):
            first = _parse_amount_relaxed(match.group(1))
            second = _parse_amount_relaxed(match.group(2))
            if first is None or second is None:
                continue
            hi = max(first, second)
            lo = min(first, second)
            if hi < 100 or lo <= 0:
                continue
            if lo > hi:
                continue
            if result["wages"] is None:
                result["wages"] = hi
            if result["federal_income_tax_withheld"] is None:
                result["federal_income_tax_withheld"] = lo
            break

    wages = result.get("wages")
    withheld = result.get("federal_income_tax_withheld")
    if wages is not None and withheld is not None and withheld > wages:
        result["federal_income_tax_withheld"] = None

    return result


def _extract_1099_nec_values(text: str) -> dict[str, float | None]:
    normalized = _normalize_ocr_amount_runs(text)
    amount_re = re.compile(r"[A-Za-z]?\d[\d,]*\.\d{2}")
    result = {"nonemployee_compensation": None}

    best_value: float | None = None
    best_score = -10
    for raw_line in normalized.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        low = line.lower()
        if "nonemployee" not in low or "compensation" not in low:
            continue

        for token in amount_re.findall(line):
            value = _parse_amount_relaxed(token)
            if value is None or value <= 0:
                continue
            if _is_suspicious_tax_value(value):
                continue

            score = 0
            if re.search(r"\b1\b", low):
                score += 3
            if "box 1" in low:
                score += 3
            if "direct sales" in low or "box 2" in low:
                score -= 2
            if value >= 100:
                score += 1

            if score > best_score:
                best_score = score
                best_value = value

    if best_value is None:
        around_box1 = re.compile(
            r"([A-Za-z]?\d[\d,]*\.\d{2})\s*(?:1\s*)?nonemployee\s*comp",
            re.IGNORECASE,
        )
        for match in around_box1.finditer(normalized):
            value = _parse_amount_relaxed(match.group(1))
            if value is None or value <= 0:
                continue
            if _is_suspicious_tax_value(value):
                continue
            best_value = value
            break

    if best_value is not None:
        result["nonemployee_compensation"] = best_value

    return result


def _extract_1040_line_value(
    text: str,
    line_number: int,
    required_keywords: tuple[str, ...] | None = None,
) -> float | None:
    amount_token = re.compile(r"\(?\$?\d[\d,]*(?:\.\d{2})?\)?-?")
    patterns = [
        re.compile(rf"(?m)^\s*{line_number}[a-zA-Z]?\s+(.+?)\s*$"),
        re.compile(rf"(?m)^\s*Line\s+{line_number}[a-zA-Z]?\s*[:\-]?\s*(.+?)\s*$", re.IGNORECASE),
    ]

    for pattern in patterns:
        for match in pattern.finditer(text):
            candidate = match.group(1)
            lowered_candidate = candidate.lower()
            if required_keywords and not any(keyword in lowered_candidate for keyword in required_keywords):
                continue
            if any(
                marker in lowered_candidate
                for marker in (
                    "enter",
                    "subtract",
                    "add",
                    "multiply",
                    "divide",
                    "worksheet",
                    "instructions",
                )
            ):
                continue
            tokens = amount_token.findall(candidate)
            if not tokens:
                continue

            ranked: list[tuple[int, int, float, str]] = []
            for idx, token in enumerate(tokens):
                value = _parse_amount(token)
                if value is None:
                    continue

                # Ignore obvious captures of the line number itself.
                if value == float(line_number) and "$" not in token and "," not in token and "." not in token:
                    continue

                score = 0
                if "$" in token or "," in token or "." in token:
                    score += 3
                if abs(value) >= 100:
                    score += 2
                elif abs(value) >= 10:
                    score += 1
                ranked.append((score, idx, value, token))

            if not ranked:
                continue

            best_score, _, value, _ = sorted(ranked, key=lambda x: (x[0], x[1]), reverse=True)[0]
            if value is not None and best_score >= 2:
                return value

    return None


def _looks_like_1040_page(text: str) -> bool:
    lowered = text.lower()
    if "instructions for form 1040" in lowered:
        return False
    if "form 1040" in lowered or "u.s. individual income tax return" in lowered:
        return True
    return False


def _apply_1040_consistency(values: dict[str, float | None]) -> dict[str, float | None]:
    total_income = values.get("total_income")
    adjusted_gross_income = values.get("adjusted_gross_income")
    deductions = values.get("deductions")
    taxable_income = values.get("taxable_income")
    total_tax = values.get("total_tax")
    total_payments = values.get("total_payments")
    refund = values.get("refund")
    amount_you_owe = values.get("amount_you_owe")

    # AGI should usually not exceed total income on Form 1040.
    if total_income is not None and adjusted_gross_income is not None:
        if adjusted_gross_income > total_income:
            values["adjusted_gross_income"] = None
            adjusted_gross_income = None

    # Taxable income should not exceed AGI on Form 1040.
    if taxable_income is not None and adjusted_gross_income is not None:
        if taxable_income > adjusted_gross_income:
            values["taxable_income"] = None

    # Deductions should not exceed AGI in normal return flow.
    if deductions is not None and adjusted_gross_income is not None:
        if deductions > adjusted_gross_income:
            values["deductions"] = None

    # A return cannot have both refund and amount owed.
    if refund is not None and amount_you_owe is not None:
        if abs(refund) >= abs(amount_you_owe):
            values["amount_you_owe"] = None
        else:
            values["refund"] = None

    # Payments and tax should not be negative.
    if total_tax is not None and total_tax < 0:
        values["total_tax"] = None
    if total_payments is not None and total_payments < 0:
        values["total_payments"] = None

    return values


def _extract_form1040_values_from_blocks(text_blocks: list[str]) -> dict[str, float | None]:
    expected_fields = [
        "total_income",
        "adjusted_gross_income",
        "deductions",
        "taxable_income",
        "total_tax",
        "total_withholding",
        "total_payments",
        "refund",
        "amount_you_owe",
    ]
    best_values: dict[str, float | None] = {field: None for field in expected_fields}

    for block in text_blocks:
        if not _looks_like_1040_page(block):
            continue
        page_values = _extract_form_values(block, "Form 1040")
        page_values = _apply_1040_consistency(page_values)

        for field_name in expected_fields:
            candidate = page_values.get(field_name)
            if candidate is None:
                continue
            if _is_suspicious_tax_value(candidate):
                continue

            existing = best_values.get(field_name)
            if existing is None or abs(candidate) > abs(existing):
                best_values[field_name] = candidate

    return best_values


def parse_tax_return_summary(file_path: Path) -> TaxReturnSummary | None:
    suffix = file_path.suffix.lower()

    text_blocks: list[str] = []
    if suffix == ".pdf":
        text_blocks = _extract_pdf_text_blocks(file_path)
    elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        image_text = _ocr_image_to_text(file_path)
        if image_text.strip():
            text_blocks = [image_text]
    else:
        return None

    if not text_blocks:
        return None

    combined_text = "\n".join(text_blocks)
    form_type = _detect_form_type(combined_text, file_path.name)
    if form_type == "Form 1040" and suffix == ".pdf":
        summary_values = _extract_form1040_values_from_blocks(text_blocks)
        # Fill non 1040 specific fields from combined text when available.
        base_values = _extract_form_values(combined_text, form_type)
        for field_name, value in base_values.items():
            if field_name not in summary_values:
                summary_values[field_name] = value
            elif summary_values[field_name] is None and value is not None:
                summary_values[field_name] = value
        summary_values = _apply_1040_consistency(summary_values)
    else:
        summary_values = _extract_form_values(combined_text, form_type)

    if suffix == ".pdf" and form_type in {"Form W-2", "Form 1099-NEC"}:
        ocr_blocks = _ocr_pdf_page_texts(file_path)
        if ocr_blocks:
            ocr_text = "\n".join(ocr_blocks)
            combined_text = f"{combined_text}\n{ocr_text}"
            summary_values = _extract_form_values(combined_text, form_type)

    if form_type == "Form W-2":
        w2_values = _extract_w2_values(combined_text)
        for field_name, value in w2_values.items():
            if value is not None:
                summary_values[field_name] = value

        wages = summary_values.get("wages")
        withheld = summary_values.get("federal_income_tax_withheld")
        if wages is not None and withheld is not None and withheld > wages:
            summary_values["federal_income_tax_withheld"] = None
        if wages is None and withheld is not None:
            summary_values["federal_income_tax_withheld"] = None

    if form_type == "Form 1099-NEC":
        nec_values = _extract_1099_nec_values(combined_text)
        for field_name, value in nec_values.items():
            if value is not None:
                summary_values[field_name] = value
        nec_value = summary_values.get("nonemployee_compensation")
        if nec_value is not None and (_is_suspicious_tax_value(nec_value) or abs(nec_value) < 10):
            summary_values["nonemployee_compensation"] = None

    if all(value is None for value in summary_values.values()) and form_type == "Unknown tax form":
        return None

    return TaxReturnSummary(
        source_file=file_path.name,
        form_type=form_type,
        filing_year=_extract_filing_year(combined_text, file_path.name),
        total_income=summary_values["total_income"],
        adjusted_gross_income=summary_values["adjusted_gross_income"],
        deductions=summary_values["deductions"],
        qualified_business_income_deduction=summary_values["qualified_business_income_deduction"],
        taxable_income=summary_values["taxable_income"],
        total_credits=summary_values["total_credits"],
        total_withholding=summary_values["total_withholding"],
        estimated_tax_payments=summary_values["estimated_tax_payments"],
        total_payments=summary_values["total_payments"],
        refund=summary_values["refund"],
        amount_you_owe=summary_values["amount_you_owe"],
        total_tax=summary_values["total_tax"],
        wages=summary_values["wages"],
        federal_income_tax_withheld=summary_values["federal_income_tax_withheld"],
        social_security_wages=summary_values["social_security_wages"],
        social_security_tax_withheld=summary_values["social_security_tax_withheld"],
        medicare_wages_and_tips=summary_values["medicare_wages_and_tips"],
        medicare_tax_withheld=summary_values["medicare_tax_withheld"],
        nonemployee_compensation=summary_values["nonemployee_compensation"],
        interest_income=summary_values["interest_income"],
        ordinary_dividends=summary_values["ordinary_dividends"],
        qualified_dividends=summary_values["qualified_dividends"],
        capital_gain_distributions=summary_values["capital_gain_distributions"],
        business_income_or_loss=summary_values["business_income_or_loss"],
        gross_receipts_or_sales=summary_values["gross_receipts_or_sales"],
        total_expenses=summary_values["total_expenses"],
        additional_income=summary_values["additional_income"],
        adjustments_to_income=summary_values["adjustments_to_income"],
    )


def summarize_tax_return_summaries(summaries: list[TaxReturnSummary]) -> pd.DataFrame:
    if not summaries:
        return pd.DataFrame()

    rows = [
        {
            "source_file": item.source_file,
            "form_type": item.form_type,
            "filing_year": item.filing_year,
            "total_income": item.total_income,
            "adjusted_gross_income": item.adjusted_gross_income,
            "deductions": item.deductions,
            "qualified_business_income_deduction": item.qualified_business_income_deduction,
            "taxable_income": item.taxable_income,
            "total_credits": item.total_credits,
            "total_withholding": item.total_withholding,
            "estimated_tax_payments": item.estimated_tax_payments,
            "total_payments": item.total_payments,
            "refund": item.refund,
            "amount_you_owe": item.amount_you_owe,
            "total_tax": item.total_tax,
            "wages": item.wages,
            "federal_income_tax_withheld": item.federal_income_tax_withheld,
            "social_security_wages": item.social_security_wages,
            "social_security_tax_withheld": item.social_security_tax_withheld,
            "medicare_wages_and_tips": item.medicare_wages_and_tips,
            "medicare_tax_withheld": item.medicare_tax_withheld,
            "nonemployee_compensation": item.nonemployee_compensation,
            "interest_income": item.interest_income,
            "ordinary_dividends": item.ordinary_dividends,
            "qualified_dividends": item.qualified_dividends,
            "capital_gain_distributions": item.capital_gain_distributions,
            "business_income_or_loss": item.business_income_or_loss,
            "gross_receipts_or_sales": item.gross_receipts_or_sales,
            "total_expenses": item.total_expenses,
            "additional_income": item.additional_income,
            "adjustments_to_income": item.adjustments_to_income,
        }
        for item in summaries
    ]

    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=["source_file"], keep="last")


def summarize_tax_form_coverage(summary: TaxReturnSummary) -> tuple[int, int, list[str]]:
    expected_by_form: dict[str, list[str]] = {
        "Form 1040": [
            "total_income",
            "adjusted_gross_income",
            "deductions",
            "taxable_income",
            "total_tax",
            "total_withholding",
            "total_payments",
            "refund",
            "amount_you_owe",
        ],
        "Schedule 1": ["additional_income", "adjustments_to_income"],
        "Schedule C": ["gross_receipts_or_sales", "total_expenses", "business_income_or_loss"],
        "Form W-2": ["wages", "federal_income_tax_withheld"],
        "Form 1099-NEC": ["nonemployee_compensation"],
        "Form 1099-MISC": ["nonemployee_compensation"],
        "Form 1099-INT": ["interest_income"],
        "Form 1099-DIV": ["ordinary_dividends"],
    }

    expected = expected_by_form.get(summary.form_type, [
        "adjusted_gross_income",
        "taxable_income",
        "total_payments",
        "refund",
        "amount_you_owe",
    ])

    missing: list[str] = []
    extracted = 0
    for field_name in expected:
        value = getattr(summary, field_name, None)
        if value is None or _is_suspicious_tax_value(value):
            missing.append(field_name)
        else:
            extracted += 1

    return extracted, len(expected), missing


def parse_tax_form_line_items(file_path: Path) -> pd.DataFrame:
    suffix = file_path.suffix.lower()

    text_blocks: list[str] = []
    if suffix == ".pdf":
        text_blocks = _extract_pdf_text_blocks(file_path)
    elif suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        image_text = _ocr_image_to_text(file_path)
        if image_text.strip():
            text_blocks = [image_text]
    else:
        return pd.DataFrame()

    if not text_blocks:
        return pd.DataFrame()

    combined_text = "\n".join(text_blocks)
    form_type = _detect_form_type(combined_text, file_path.name)
    filing_year = _extract_filing_year(combined_text, file_path.name)
    amount_token = re.compile(r"\(?\$?\d[\d,]*(?:\.\d{2})?\)?-?")
    line_num_pattern = re.compile(r"^\s*(\d{1,2}[a-zA-Z]?)\b")
    tax_keywords = (
        "line ",
        "box ",
        "wages",
        "income",
        "tax",
        "withheld",
        "deduction",
        "credit",
        "payment",
        "refund",
        "owe",
        "dividend",
        "interest",
        "compensation",
        "gross receipts",
        "expenses",
        "adjusted gross",
        "agi",
        "taxable",
        "schedule",
        "form",
    )
    noise_fragments = (
        "www.irs.gov",
        "department of the treasury",
        "internal revenue service",
        "omb no",
        "for disclosure",
        "privacy act",
        "paperwork reduction act",
        "instructions",
        "cat. no",
        "separate instructions",
    )

    rows: list[dict[str, object]] = []
    seen: set[tuple[str, str, float]] = set()

    def _pick_best_token(tokens: list[str], line_no: str) -> tuple[str, float] | None:
        ranked: list[tuple[int, int, str, float]] = []
        for idx, token in enumerate(tokens):
            value = _parse_amount(token)
            if value is None:
                continue

            score = 0
            if "$" in token or "," in token or "." in token:
                score += 3
            if abs(value) >= 100:
                score += 2
            elif abs(value) >= 10:
                score += 1

            if line_no:
                line_num_match = re.match(r"^(\d+)", line_no)
                if line_num_match:
                    line_base = float(line_num_match.group(1))
                    if value == line_base and "$" not in token and "," not in token and "." not in token:
                        continue

            ranked.append((score, idx, token, value))

        if not ranked:
            return None

        score, _, token, value = sorted(ranked, key=lambda x: (x[0], x[1]), reverse=True)[0]
        if score <= 0:
            return None
        return token, value

    for raw_line in combined_text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        lowered_line = line.lower()
        has_line_no = bool(line_num_pattern.match(line))
        has_tax_keyword = any(keyword in lowered_line for keyword in tax_keywords)
        has_noise_fragment = any(fragment in lowered_line for fragment in noise_fragments)
        if has_noise_fragment:
            continue

        tokens = amount_token.findall(line)
        if not tokens:
            continue

        looks_like_currency = any("$" in token or "," in token or "." in token for token in tokens)
        if not (looks_like_currency or has_line_no or has_tax_keyword):
            continue

        line_no_match = line_num_pattern.match(line)
        line_no = line_no_match.group(1) if line_no_match else ""

        token_pick = _pick_best_token(tokens, line_no)
        if token_pick is None:
            continue
        selected_token, value = token_pick
        if abs(value) > 100_000_000:
            continue

        label = line
        if line_no_match:
            label = label[line_no_match.end():].strip()
        amount_pos = label.rfind(selected_token)
        if amount_pos > 0:
            label = label[:amount_pos]
        label = label.strip(" .:-")
        if len(label) < 5:
            continue
        if not re.search(r"[A-Za-z]", label):
            continue
        if label.lower() in {"line", "amount", "total", "form", "box"}:
            continue
        if any(fragment in label.lower() for fragment in noise_fragments):
            continue
        if not label:
            label = line

        dedupe_key = (line_no, label.lower(), value)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        rows.append(
            {
                "source_file": file_path.name,
                "form_type": form_type,
                "filing_year": filing_year,
                "line_number": line_no,
                "field_label": label,
                "value": value,
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    return df.sort_values(by=["source_file", "line_number", "field_label", "value"], ascending=[True, True, True, False])


def summarize_tax_form_line_items(line_item_frames: list[pd.DataFrame]) -> pd.DataFrame:
    if not line_item_frames:
        return pd.DataFrame()

    valid_frames = [df for df in line_item_frames if not df.empty]
    if not valid_frames:
        return pd.DataFrame()

    combined = pd.concat(valid_frames, ignore_index=True)
    cleaned = combined.drop_duplicates(subset=["source_file", "line_number", "field_label", "value"], keep="first")

    if "field_label" not in cleaned.columns:
        return cleaned

    label_series = cleaned["field_label"].astype(str).str.strip()
    lowered = label_series.str.lower()

    noise_patterns = [
        r"^\$",
        r"^\$+$",
        r"^,?\d{1,3}(?:,\d{3})*$",
        r"^,\d+$",
        r"^form\(s\)$",
        r"^go to www\.irs\.gov/form",
        r"^enter the amount from",
        r"^enter the smaller of",
        r"^enter the sum of",
        r"^attach form",
        r"^complete a separate",
        r"^include on your",
        r"^leave this line blank",
        r"^if your",
        r"^from form",
        r"^amount from line",
        r"^enter\b",
        r"^subtract\b",
        r"^add\b",
        r"^multiply\b",
        r"^divide\b",
        r"^section$",
        r"^from line$",
        r"^on line$",
        r"^\(\$",
        r"^maximum taxable income per this bracket",
        r"^year property$",
    ]

    keep_mask = label_series.str.len().ge(5) & label_series.str.contains(r"[A-Za-z]", regex=True)
    for pattern in noise_patterns:
        keep_mask &= ~lowered.str.contains(pattern, regex=True)

    keep_mask &= ~lowered.str.contains(r"www\.irs\.gov|cat\. no|privacy act|paperwork reduction act", regex=True)
    keep_mask &= ~lowered.str.contains(r"if married filing separately|qualifying surviving spouse|head of household", regex=True)

    filtered = cleaned[keep_mask].copy()
    return filtered.sort_values(by=["source_file", "line_number", "field_label", "value"], ascending=[True, True, True, False])


def summarize_transactions(transactions: list[Transaction]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame()

    rows = [
        {
            "source_file": tx.source_file,
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "category": tx.category,
            "confidence": round(tx.confidence, 2),
            "note": tx.note,
            "deductible_status": tx.deductible_status,
            "deductible_note": tx.deductible_note,
        }
        for tx in transactions
    ]

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["source_file", "date", "description", "amount"], keep="first")
    return df.sort_values(by=["category", "date"], ascending=[True, True])


def load_transactions_from_csv(file_path: Path) -> list[Transaction]:
    if not file_path.exists() or file_path.suffix.lower() != ".csv":
        return []

    try:
        df = pd.read_csv(file_path)
    except Exception:
        return []

    required_columns = {
        "source_file",
        "date",
        "description",
        "amount",
        "category",
        "confidence",
        "note",
        "deductible_status",
        "deductible_note",
    }
    if not required_columns.issubset(set(df.columns)):  # type: ignore[arg-type]
        return []

    transactions: list[Transaction] = []
    for _, row in df.iterrows():
        try:
            transactions.append(
                Transaction(
                    source_file=str(row["source_file"]),
                    date=str(row["date"]),
                    description=str(row["description"]),
                    amount=float(row["amount"]),
                    category=str(row["category"]),
                    confidence=float(row["confidence"]),
                    note=str(row["note"]),
                    deductible_status=str(row["deductible_status"]),
                    deductible_note=str(row["deductible_note"]),
                )
            )
        except Exception:
            continue

    return transactions


def load_transactions_from_folder(folder_path: Path) -> list[Transaction]:
    if not folder_path.exists() or not folder_path.is_dir():
        return []

    transactions: list[Transaction] = []
    skip_names = {
        "combined_extracted.csv",
        "tax_review_combined_extracted.csv",
    }
    for csv_path in sorted(folder_path.rglob("*.csv")):
        if csv_path.name in skip_names:
            continue
        transactions.extend(load_transactions_from_csv(csv_path))

    return transactions
