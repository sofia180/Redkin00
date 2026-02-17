import os
from dotenv import load_dotenv

ENV_FILE = os.getenv("ENV_FILE", ".env")
load_dotenv(ENV_FILE, override=True)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _format_money(value: int) -> str:
    return f"{value:,}".replace(",", " ")


BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required")

ADMIN_IDS = {int(x) for x in _split_csv(os.getenv("ADMIN_IDS", "")) if x.isdigit()}

# Niche settings
NICHE_NAME = os.getenv("NICHE_NAME", "Ипотека")
CURRENCY_SYMBOL = os.getenv("CURRENCY_SYMBOL", "$")

# Messaging overrides (optional)
INTRO_TEXT = os.getenv(
    "INTRO_TEXT",
    f"Привет! Я помогу вам подобрать {NICHE_NAME.lower()}.\n"
    "Ответьте на несколько вопросов — это займёт всего пару минут.",
)
QUESTION_NAME = os.getenv("QUESTION_NAME", "Как вас зовут?")
QUESTION_PHONE = os.getenv("QUESTION_PHONE", "Поделитесь, пожалуйста, вашим номером телефона.")
QUESTION_EMAIL = os.getenv("QUESTION_EMAIL", "Можете оставить email для получения подробностей.")
QUESTION_BUDGET = os.getenv("QUESTION_BUDGET", "Какую сумму кредита планируете?")
QUESTION_REGION = os.getenv("QUESTION_REGION", "В каком регионе хотите взять ипотеку?")
QUESTION_TIMEFRAME = os.getenv("QUESTION_TIMEFRAME", "Когда планируете оформить ипотеку?")
QUESTION_CONTACTED = os.getenv("QUESTION_CONTACTED", "Уже обращались к банкам или брокерам?")
THANK_YOU_MESSAGE = os.getenv(
    "THANK_YOU_MESSAGE",
    "Спасибо! Мы получили вашу заявку и свяжемся с вами в ближайшее время.",
)
DUPLICATE_MESSAGE = os.getenv(
    "DUPLICATE_MESSAGE",
    "Спасибо! Мы уже получили заявку с этим номером и скоро свяжемся.",
)

# Budget brackets
BUDGET_LOW_MAX = int(os.getenv("BUDGET_LOW_MAX", "100000"))
BUDGET_MID_MAX = int(os.getenv("BUDGET_MID_MAX", "300000"))

BUDGET_OPTIONS = [
    {
        "key": "low",
        "label": f"До {_format_money(BUDGET_LOW_MAX)}{CURRENCY_SYMBOL}",
        "min": 0,
        "max": BUDGET_LOW_MAX,
    },
    {
        "key": "mid",
        "label": f"{_format_money(BUDGET_LOW_MAX)}–{_format_money(BUDGET_MID_MAX)}{CURRENCY_SYMBOL}",
        "min": BUDGET_LOW_MAX,
        "max": BUDGET_MID_MAX,
    },
    {
        "key": "high",
        "label": f"Более {_format_money(BUDGET_MID_MAX)}{CURRENCY_SYMBOL}",
        "min": BUDGET_MID_MAX,
        "max": None,
    },
]

# Timeframes
TIMEFRAME_OPTIONS = [
    {"key": "week", "label": "В течение недели", "max_days": 7},
    {"key": "month", "label": "В течение месяца", "max_days": 30},
    {"key": "quarter", "label": "Через 1–3 месяца", "max_days": 90},
]

# Segmentation rules
HOT_BUDGET_MIN = int(os.getenv("HOT_BUDGET_MIN", str(BUDGET_LOW_MAX)))
HOT_MAX_DAYS = int(os.getenv("HOT_MAX_DAYS", "30"))
WARM_BUDGET_MIN = int(os.getenv("WARM_BUDGET_MIN", str(BUDGET_LOW_MAX)))
WARM_MAX_DAYS = int(os.getenv("WARM_MAX_DAYS", "90"))

LEAD_STATUS_LABELS = {
    "hot": "Горячий",
    "warm": "Тёплый",
    "cold": "Холодный",
}

# Optional region list (comma-separated). If empty, free text is used.
REGION_OPTIONS = _split_csv(os.getenv("REGION_OPTIONS", ""))

# Form toggles
ASK_EMAIL = os.getenv("ASK_EMAIL", "1") == "1"

# Validation
PHONE_MIN_DIGITS = int(os.getenv("PHONE_MIN_DIGITS", "10"))

# Integrations
CRM_WEBHOOK_URL = os.getenv("CRM_WEBHOOK_URL", "")
GOOGLE_SHEETS_WEBHOOK_URL = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "")
GOOGLE_SHEETS_CSV_PATH = os.getenv("GOOGLE_SHEETS_CSV_PATH", "")
WEBHOOK_TIMEOUT_SECONDS = int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "10"))

# Duplicate handling
NOTIFY_ON_DUPLICATE = os.getenv("NOTIFY_ON_DUPLICATE", "0") == "1"
