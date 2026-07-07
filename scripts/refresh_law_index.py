from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tax_agent.config import get_settings
from tax_agent.law_ingest import build_law_index


def main() -> None:
    settings = get_settings()
    active_db = settings.law_db_path
    refresh_db = settings.data_dir / "law_index_refresh.db"

    if refresh_db.exists():
        refresh_db.unlink()

    os.environ["LAW_DB_PATH"] = str(refresh_db)
    max_pages_override = os.getenv("LAW_MAX_PAGES", "").strip()
    if max_pages_override:
        print(f"Using LAW_MAX_PAGES override: {max_pages_override}")
    stats = build_law_index()

    report_dir = settings.cache_dir / "refresh_reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"refresh_{timestamp}.json"
    try:
        if active_db.exists():
            active_db.unlink()
        shutil.move(str(refresh_db), str(active_db))
        stats["active_db_swapped"] = True
    except Exception:
        stats["active_db_swapped"] = False
        stats["refresh_db_path"] = str(refresh_db)
        stats["active_db_path"] = str(active_db)

    report_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(f"Refresh complete: {report_path}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
