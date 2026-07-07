from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    project_root: Path
    data_dir: Path
    uploads_dir: Path
    cache_dir: Path
    law_db_path: Path
    openai_api_key: str | None
    model_name: str


def get_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / "data"
    uploads_dir = data_dir / "uploads"
    cache_dir = data_dir / "law_cache"
    law_db_env = os.getenv("LAW_DB_PATH", "").strip()
    primary_law_db = Path(law_db_env) if law_db_env else (data_dir / "law_index.db")
    refresh_law_db = data_dir / "law_index_refresh.db"

    def _has_sources(db_path: Path) -> bool:
        if not db_path.exists():
            return False
        try:
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='sources'"
                ).fetchone()
                if not row or row[0] == 0:
                    return False
                count_row = conn.execute("SELECT COUNT(*) FROM sources").fetchone()
                return bool(count_row and count_row[0] > 0)
        except sqlite3.Error:
            return False

    if _has_sources(primary_law_db):
        law_db_path = primary_law_db
    elif _has_sources(refresh_law_db):
        law_db_path = refresh_law_db
    else:
        law_db_path = primary_law_db

    uploads_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        uploads_dir=uploads_dir,
        cache_dir=cache_dir,
        law_db_path=law_db_path,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        model_name=os.getenv("MODEL_NAME", "gpt-5.3-codex"),
    )
