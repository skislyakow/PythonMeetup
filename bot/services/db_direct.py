from datetime import datetime
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "meetup.db"


def create_event(speaker_id: int, title: str, start_time: datetime, end_time: datetime) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            "INSERT INTO events (speaker_id, title, start_time, end_time, is_active) "
            "VALUES (?, ?, ?, ?, 0)",
            [speaker_id, title, start_time.strftime("%Y-%m-%d %H:%M:%S"), end_time.strftime("%Y-%m-%d %H:%M:%S")],
        )
        conn.commit()
    finally:
        conn.close()
