import sqlite3
import hashlib
import re
from pathlib import Path
from core.config import CACHE_DB_PATH

class TranslationCache:
    """Thread-safe SQLite persistent cache for translated text."""
    
    CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")

    def __init__(self, db_path: Path = CACHE_DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path, timeout=15)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS translations (
                    hash TEXT PRIMARY KEY,
                    source_lang TEXT,
                    target_lang TEXT,
                    original_text TEXT,
                    translated_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON translations(hash)")
            conn.commit()

    @staticmethod
    def _compute_hash(text: str, source_lang: str, target_lang: str) -> str:
        key = f"{source_lang}:{target_lang}:{text.strip()}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def get(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> str | None:
        if not text or not text.strip():
            return text
        h = self._compute_hash(text, source_lang, target_lang)
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT translated_text FROM translations WHERE hash = ?", (h,))
            row = cursor.fetchone()
            if row:
                res = row[0]
                if target_lang == "en" and self.CYRILLIC_RE.search(res):
                    return None
                return res
            return None

    def set(self, text: str, translated_text: str, source_lang: str = "auto", target_lang: str = "en"):
        if not text or not text.strip() or not translated_text:
            return
        # Never cache Cyrillic text as an English translation
        if target_lang == "en" and self.CYRILLIC_RE.search(translated_text):
            return
        h = self._compute_hash(text, source_lang, target_lang)
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO translations 
                (hash, source_lang, target_lang, original_text, translated_text)
                VALUES (?, ?, ?, ?, ?)
            """, (h, source_lang, target_lang, text, translated_text))
            conn.commit()

    def set_many(self, items: list):
        """High-speed batch insert to avoid SQLite lock contention across threads."""
        if not items:
            return
        records = []
        for text, trans, sl, tl in items:
            if not text or not text.strip() or not trans:
                continue
            if tl == "en" and self.CYRILLIC_RE.search(trans):
                continue
            h = self._compute_hash(text, sl, tl)
            records.append((h, sl, tl, text, trans))
        if not records:
            return
        with self._get_conn() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO translations 
                (hash, source_lang, target_lang, original_text, translated_text)
                VALUES (?, ?, ?, ?, ?)
            """, records)
            conn.commit()

    def get_count(self) -> int:
        """Returns total number of cached translation pairs."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM translations")
            row = cursor.fetchone()
            return row[0] if row else 0

    def clear(self):
        """Clears all cached translations."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM translations")
            conn.commit()

