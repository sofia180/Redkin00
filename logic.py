from __future__ import annotations

from typing import Any

from config import (
    BUDGET_OPTIONS,
    TIMEFRAME_OPTIONS,
    HOT_BUDGET_MIN,
    HOT_MAX_DAYS,
    WARM_BUDGET_MIN,
    WARM_MAX_DAYS,
    LEAD_STATUS_LABELS,
)


def get_budget_option(key: str) -> dict[str, Any] | None:
    for option in BUDGET_OPTIONS:
        if option["key"] == key:
            return option
    return None


def get_timeframe_option(key: str) -> dict[str, Any] | None:
    for option in TIMEFRAME_OPTIONS:
        if option["key"] == key:
            return option
    return None


def segment_lead(budget_key: str, timeframe_key: str) -> str:
    budget = get_budget_option(budget_key) or {"min": 0}
    timeframe = get_timeframe_option(timeframe_key) or {"max_days": 999999}

    budget_value = int(budget.get("min") or 0)
    max_days = int(timeframe.get("max_days") or 999999)

    if budget_value >= HOT_BUDGET_MIN and max_days <= HOT_MAX_DAYS:
        return "hot"
    if budget_value >= WARM_BUDGET_MIN and max_days <= WARM_MAX_DAYS:
        return "warm"
    return "cold"


def status_label(status: str) -> str:
    return LEAD_STATUS_LABELS.get(status, status)


def format_lead_message(lead: dict[str, Any]) -> str:
    return (
        "🔥 Новый ЛИД\n"
        f"Статус: {status_label(lead['status'])}\n"
        f"Имя: {lead.get('name') or '-'}\n"
        f"Телефон: {lead.get('phone') or '-'}\n"
        f"Email: {lead.get('email') or '-'}\n"
        f"Сумма: {lead.get('budget_label') or '-'}\n"
        f"Регион: {lead.get('region') or '-'}\n"
        f"Срок: {lead.get('timeframe_label') or '-'}\n"
        f"Обращались: {lead.get('contacted_before_label') or '-'}"
    )
