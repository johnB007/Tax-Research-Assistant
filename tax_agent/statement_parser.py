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


DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"),
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"^(\d{1,2}/\d{2})\b"),  # Chase: MM/DD at line start
]

AMOUNT_PATTERN = re.compile(r"(-?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*$")
_RAPID_OCR_ENGINE: object | None = None


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
                return pytesseract.image_to_string(image)
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
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()
            if has_tesseract:
                text = pytesseract.image_to_string(pil_image)
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
    try:
        return float(clean)
    except ValueError:
        return None


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
    found_text = False

    try:
        reader = PdfReader(str(file_path))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                reader = None

        if reader is not None:
            for page in reader.pages:
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                if text.strip():
                    found_text = True
                    transactions.extend(_transactions_from_text(file_path.name, text))
    except Exception:
        found_text = False

    if not found_text or not transactions:
        for ocr_text in _ocr_pdf_page_texts(file_path):
            transactions.extend(_transactions_from_text(file_path.name, ocr_text))

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
