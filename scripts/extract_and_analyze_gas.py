"""Extract all six 4157 statements to CSV and print gas totals by month."""
from __future__ import annotations
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[1]))

from pathlib import Path
from tax_agent.statement_parser import parse_statement, summarize_transactions

FOLDER = Path(r"C:\Users\jobarbar\OneDrive - Microsoft\Desktop\Financial\FY2026\Credit Card Statement")
OUT_DIR = FOLDER  # CSVs are saved next to the source PDFs
OUT_DIR.mkdir(parents=True, exist_ok=True)

all_rows = []
for pdf in sorted(FOLDER.glob("*4157*.pdf")):
    txns = parse_statement(pdf)
    df = summarize_transactions(txns)
    csv_path = OUT_DIR / (pdf.stem + "_extracted.csv")
    if not df.empty:
        df.to_csv(csv_path, index=False)
        all_rows.append(df)
    print(f"{pdf.name}: {len(df)} rows  ->  {csv_path.name}")

if not all_rows:
    print("No transactions extracted from any file.")
    raise SystemExit(1)

import pandas as pd

combined = pd.concat(all_rows, ignore_index=True)
combined_path = OUT_DIR / "combined_all_statements.csv"
combined.to_csv(combined_path, index=False)
print(f"\nCombined: {len(combined)} rows  ->  {combined_path.name}")

# Gas analysis: match known fuel merchants, exclude payment/credit rows
import re as _re

_GAS_MERCHANTS = _re.compile(
    r"\b(shell|exxon|mobil(?!\s*app|\s*pay)|bp\b|chevron|circle\s*k|wawa|speedway"
    r"|marathon|kwiktrip|kwik\s*trip|gas\s*station|fuel|racetrac|sunoco|refuel"
    r"|pilot\s+\d|loves|casey|sheetz|valero)\b",
    _re.IGNORECASE,
)

_PAYMENT_RE = _re.compile(r"payment|autopay|thank\s+you", _re.IGNORECASE)

gas_mask = (
    (
        combined["category"].str.lower().str.contains("vehicle", na=False)
        | combined["description"].apply(lambda d: bool(_GAS_MERCHANTS.search(str(d))))
    )
    & ~combined["description"].apply(lambda d: bool(_PAYMENT_RE.search(str(d))))
    & (combined["amount"] > 0)
)

gas_df = combined[gas_mask].copy()
gas_df["month"] = pd.to_datetime(gas_df["date"], errors="coerce").dt.to_period("M")
gas_csv = OUT_DIR / "gas_transactions.csv"
gas_df.to_csv(gas_csv, index=False)
print(f"\nGas transactions: {len(gas_df)} rows  ->  {gas_csv.name}")

if not gas_df.empty:
    monthly = gas_df.groupby("month")["amount"].sum().reset_index()
    monthly.columns = ["month", "total_gas_spend"]
    print("\nMonthly gas totals:")
    print(monthly.to_string(index=False))
    six_month_total = monthly["total_gas_spend"].sum()
    print(f"\nSix month total: ${six_month_total:,.2f}")
    monthly_csv = OUT_DIR / "gas_monthly_totals.csv"
    monthly.to_csv(monthly_csv, index=False)
    print(f"\nSaved  ->  {monthly_csv.name}")
else:
    print("\nNo gas transactions matched. Printing unique categories and sample descriptions for review:")
    print(combined["category"].value_counts().head(20).to_string())
    print("\nSample descriptions:")
    print(combined["description"].drop_duplicates().head(40).to_string())
