from __future__ import annotations

import csv
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import httpx

from config import (
    CRM_WEBHOOK_URL,
    GOOGLE_SHEETS_WEBHOOK_URL,
    GOOGLE_SHEETS_CSV_PATH,
    WEBHOOK_TIMEOUT_SECONDS,
    NICHE_NAME,
)

DB_PATH = Path(__file__).with_name("leads.db")


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                name TEXT,
                phone TEXT UNIQUE NOT NULL,
                email TEXT,
                budget_key TEXT,
                budget_label TEXT,
                region TEXT,
                timeframe_key TEXT,
                timeframe_label TEXT,
                contacted_before TEXT,
                status TEXT,
                duplicate_count INTEGER DEFAULT 0,
                raw_payload TEXT
            );
            """
        )


def save_lead(lead: dict[str, Any]) -> tuple[int, bool]:
    with get_conn() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO leads (
                    name, phone, email, budget_key, budget_label, region,
                    timeframe_key, timeframe_label, contacted_before, status, raw_payload
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    lead.get("name"),
                    lead.get("phone"),
                    lead.get("email"),
                    lead.get("budget_key"),
                    lead.get("budget_label"),
                    lead.get("region"),
                    lead.get("timeframe_key"),
                    lead.get("timeframe_label"),
                    lead.get("contacted_before"),
                    lead.get("status"),
                    json.dumps(lead, ensure_ascii=False),
                ),
            )
            return int(cur.lastrowid), False
        except sqlite3.IntegrityError:
            conn.execute(
                """
                UPDATE leads
                SET updated_at=CURRENT_TIMESTAMP,
                    name=?,
                    email=?,
                    budget_key=?,
                    budget_label=?,
                    region=?,
                    timeframe_key=?,
                    timeframe_label=?,
                    contacted_before=?,
                    status=?,
                    duplicate_count=duplicate_count+1,
                    raw_payload=?
                WHERE phone=?
                """,
                (
                    lead.get("name"),
                    lead.get("email"),
                    lead.get("budget_key"),
                    lead.get("budget_label"),
                    lead.get("region"),
                    lead.get("timeframe_key"),
                    lead.get("timeframe_label"),
                    lead.get("contacted_before"),
                    lead.get("status"),
                    json.dumps(lead, ensure_ascii=False),
                    lead.get("phone"),
                ),
            )
            row = conn.execute("SELECT id FROM leads WHERE phone=?", (lead.get("phone"),)).fetchone()
            return int(row["id"]) if row else 0, True


def stats() -> dict[str, int]:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM leads").fetchone()["c"]
        hot = conn.execute("SELECT COUNT(*) AS c FROM leads WHERE status='hot'").fetchone()["c"]
        warm = conn.execute("SELECT COUNT(*) AS c FROM leads WHERE status='warm'").fetchone()["c"]
        cold = conn.execute("SELECT COUNT(*) AS c FROM leads WHERE status='cold'").fetchone()["c"]
    return {"total": total, "hot": hot, "warm": warm, "cold": cold}


def export_leads_csv(start: date, end: date, output_path: Path) -> Path:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT created_at, name, phone, email, budget_label, region, timeframe_label, status
            FROM leads
            WHERE date(created_at) BETWEEN date(?) AND date(?)
            ORDER BY created_at ASC
            """,
            (start.isoformat(), end.isoformat()),
        ).fetchall()

    headers = [
        "created_at",
        "name",
        "phone",
        "email",
        "budget",
        "region",
        "timeframe",
        "status",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(
                [
                    row["created_at"],
                    row["name"],
                    row["phone"],
                    row["email"],
                    row["budget_label"],
                    row["region"],
                    row["timeframe_label"],
                    row["status"],
                ]
            )

    return output_path


async def push_to_integrations(lead: dict[str, Any]) -> None:
    payload = {
        "niche": NICHE_NAME,
        "created_at": lead.get("created_at"),
        "name": lead.get("name"),
        "phone": lead.get("phone"),
        "email": lead.get("email"),
        "budget": lead.get("budget_label"),
        "budget_key": lead.get("budget_key"),
        "region": lead.get("region"),
        "timeframe": lead.get("timeframe_label"),
        "timeframe_key": lead.get("timeframe_key"),
        "contacted_before": lead.get("contacted_before"),
        "status": lead.get("status"),
    }

    await _post_webhook(CRM_WEBHOOK_URL, payload)
    await _post_webhook(GOOGLE_SHEETS_WEBHOOK_URL, payload)

    if GOOGLE_SHEETS_CSV_PATH:
        _append_csv(Path(GOOGLE_SHEETS_CSV_PATH), payload)


async def _post_webhook(url: str, payload: dict[str, Any]) -> None:
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            if response.status_code >= 400:
                logging.error(
                    "Webhook push failed: %s status=%s body=%s",
                    url,
                    response.status_code,
                    response.text[:500],
                )
    except Exception:
        logging.exception("Webhook push failed: %s", url)


def _append_csv(path: Path, payload: dict[str, Any]) -> None:
    headers = [
        "created_at",
        "name",
        "phone",
        "email",
        "budget",
        "budget_key",
        "region",
        "timeframe",
        "timeframe_key",
        "contacted_before",
        "status",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "created_at": payload.get("created_at"),
                "name": payload.get("name"),
                "phone": payload.get("phone"),
                "email": payload.get("email"),
                "budget": payload.get("budget"),
                "budget_key": payload.get("budget_key"),
                "region": payload.get("region"),
                "timeframe": payload.get("timeframe"),
                "timeframe_key": payload.get("timeframe_key"),
                "contacted_before": payload.get("contacted_before"),
                "status": payload.get("status"),
            }
        )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
