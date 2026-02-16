import asyncio
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    FSInputFile,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app_logging import setup_logging
from config import (
    ADMIN_IDS,
    ASK_EMAIL,
    BOT_TOKEN,
    NICHE_NAME,
    PHONE_MIN_DIGITS,
    REGION_OPTIONS,
    TIMEFRAME_OPTIONS,
    BUDGET_OPTIONS,
    NOTIFY_ON_DUPLICATE,
)
from logic import (
    get_budget_option,
    get_timeframe_option,
    segment_lead,
    status_label,
    format_lead_message,
)
from states import LeadForm
from storage import init_db, save_lead, stats as lead_stats, export_leads_csv, push_to_integrations

router = Router()


def is_admin(user_id: int | None) -> bool:
    return bool(user_id) and user_id in ADMIN_IDS


def normalize_phone(text: str) -> str | None:
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    if len(digits) < PHONE_MIN_DIGITS:
        return None
    return digits


def is_valid_email(text: str) -> bool:
    if not text or "@" not in text:
        return False
    local, _, domain = text.partition("@")
    return bool(local.strip()) and "." in domain


def build_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Начать", callback_data="lead_start")]]
    )


def build_budget_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in BUDGET_OPTIONS:
        builder.button(text=option["label"], callback_data=f"budget:{option['key']}")
    builder.adjust(1)
    return builder.as_markup()


def build_timeframe_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in TIMEFRAME_OPTIONS:
        builder.button(text=option["label"], callback_data=f"timeframe:{option['key']}")
    builder.adjust(1)
    return builder.as_markup()


def build_yes_no_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да", callback_data=f"{prefix}:yes"),
                InlineKeyboardButton(text="Нет", callback_data=f"{prefix}:no"),
            ]
        ]
    )


def build_region_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for region in REGION_OPTIONS:
        builder.button(text=region, callback_data=f"region:{region}")
    builder.adjust(1)
    return builder.as_markup()


def build_contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def ask_budget(message: Message, state: FSMContext) -> None:
    await state.set_state(LeadForm.budget)
    await message.answer("Какую сумму кредита планируете?", reply_markup=build_budget_keyboard())


async def ask_region(message: Message, state: FSMContext) -> None:
    await state.set_state(LeadForm.region)
    if REGION_OPTIONS:
        await message.answer("В каком регионе хотите взять ипотеку?", reply_markup=build_region_keyboard())
        return
    await message.answer("В каком регионе хотите взять ипотеку?")


async def ask_timeframe(message: Message, state: FSMContext) -> None:
    await state.set_state(LeadForm.timeframe)
    await message.answer("Когда планируете оформить ипотеку?", reply_markup=build_timeframe_keyboard())


async def ask_contacted(message: Message, state: FSMContext) -> None:
    await state.set_state(LeadForm.contacted)
    await message.answer("Уже обращались к банкам или брокерам?", reply_markup=build_yes_no_keyboard("contacted"))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    greeting = (
        f"Привет! Я помогу вам подобрать {NICHE_NAME.lower()}.\n"
        "Ответьте на несколько вопросов — это займёт всего пару минут."
    )
    await message.answer(greeting, reply_markup=build_start_keyboard())


@router.callback_query(F.data == "lead_start")
async def lead_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(LeadForm.name)
    await callback.message.answer("Как вас зовут?")
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Ок, отменил. Чтобы начать заново, отправьте /start.")


@router.message(LeadForm.name)
async def lead_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Пожалуйста, напишите ваше имя.")
        return
    await state.update_data(name=name)
    await state.set_state(LeadForm.phone)
    await message.answer(
        "Поделитесь, пожалуйста, вашим номером телефона.",
        reply_markup=build_contact_keyboard(),
    )


@router.message(LeadForm.phone)
async def lead_phone(message: Message, state: FSMContext) -> None:
    phone_raw = ""
    if message.contact:
        phone_raw = message.contact.phone_number or ""
    else:
        phone_raw = message.text or ""

    phone = normalize_phone(phone_raw)
    if not phone:
        await message.answer(
            f"Не удалось распознать номер. Введите телефон в формате +7XXXXXXXXXX (мин. {PHONE_MIN_DIGITS} цифр)."
        )
        return

    await state.update_data(phone=phone)
    await message.answer("Спасибо!", reply_markup=ReplyKeyboardRemove())

    if ASK_EMAIL:
        await state.set_state(LeadForm.email)
        skip_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Пропустить", callback_data="skip_email")]]
        )
        await message.answer("Можете оставить email для получения подробностей.", reply_markup=skip_keyboard)
        return

    await ask_budget(message, state)


@router.callback_query(LeadForm.email, F.data == "skip_email")
async def lead_email_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(email=None)
    await callback.answer()
    await ask_budget(callback.message, state)


@router.message(LeadForm.email)
async def lead_email(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text.lower() in {"пропустить", "skip", "нет"}:
        await state.update_data(email=None)
        await ask_budget(message, state)
        return

    if not is_valid_email(text):
        await message.answer("Похоже на некорректный email. Попробуйте ещё раз или нажмите «Пропустить».")
        return

    await state.update_data(email=text)
    await ask_budget(message, state)


@router.callback_query(LeadForm.budget, F.data.startswith("budget:"))
async def lead_budget(callback: CallbackQuery, state: FSMContext) -> None:
    budget_key = callback.data.split(":", 1)[1]
    option = get_budget_option(budget_key)
    if not option:
        await callback.answer("Выберите вариант из списка.")
        return

    await state.update_data(budget_key=budget_key, budget_label=option["label"])
    await callback.answer()
    await ask_region(callback.message, state)


@router.callback_query(LeadForm.region, F.data.startswith("region:"))
async def lead_region_choice(callback: CallbackQuery, state: FSMContext) -> None:
    region = callback.data.split(":", 1)[1]
    await state.update_data(region=region)
    await callback.answer()
    await ask_timeframe(callback.message, state)


@router.message(LeadForm.region)
async def lead_region(message: Message, state: FSMContext) -> None:
    region = (message.text or "").strip()
    if not region:
        await message.answer("Пожалуйста, укажите регион.")
        return
    await state.update_data(region=region)
    await ask_timeframe(message, state)


@router.callback_query(LeadForm.timeframe, F.data.startswith("timeframe:"))
async def lead_timeframe(callback: CallbackQuery, state: FSMContext) -> None:
    timeframe_key = callback.data.split(":", 1)[1]
    option = get_timeframe_option(timeframe_key)
    if not option:
        await callback.answer("Выберите вариант из списка.")
        return

    await state.update_data(timeframe_key=timeframe_key, timeframe_label=option["label"])
    await callback.answer()
    await ask_contacted(callback.message, state)


@router.callback_query(LeadForm.contacted, F.data.startswith("contacted:"))
async def lead_contacted(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":", 1)[1]
    contacted_label = "Да" if value == "yes" else "Нет"
    await state.update_data(contacted_before=value, contacted_before_label=contacted_label)
    await callback.answer()
    await finalize_lead(callback.message, state)


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("Нет доступа.")
        return
    data = lead_stats()
    await message.answer(
        "Статистика лидов:\n"
        f"Всего: {data['total']}\n"
        f"Горячих: {data['hot']}\n"
        f"Тёплых: {data['warm']}\n"
        f"Холодных: {data['cold']}"
    )


@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    if not is_admin(message.from_user.id if message.from_user else None):
        await message.answer("Нет доступа.")
        return

    parts = (message.text or "").split()
    if len(parts) == 3:
        start = parse_date(parts[1])
        end = parse_date(parts[2])
        if not start or not end:
            await message.answer("Формат: /export YYYY-MM-DD YYYY-MM-DD")
            return
    elif len(parts) == 2:
        start = parse_date(parts[1])
        if not start:
            await message.answer("Формат: /export YYYY-MM-DD YYYY-MM-DD")
            return
        end = date.today()
    else:
        end = date.today()
        start = end - timedelta(days=30)

    filename = f"leads_{start.isoformat()}_{end.isoformat()}.csv"
    export_path = Path("/tmp") / filename
    export_leads_csv(start, end, export_path)

    await message.answer_document(FSInputFile(export_path))


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


async def finalize_lead(message: Message, state: FSMContext) -> None:
    data = await state.get_data()

    budget_key = data.get("budget_key")
    timeframe_key = data.get("timeframe_key")
    status = segment_lead(budget_key, timeframe_key)

    lead = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": data.get("name"),
        "phone": data.get("phone"),
        "email": data.get("email"),
        "budget_key": budget_key,
        "budget_label": data.get("budget_label"),
        "region": data.get("region"),
        "timeframe_key": timeframe_key,
        "timeframe_label": data.get("timeframe_label"),
        "contacted_before": data.get("contacted_before"),
        "contacted_before_label": data.get("contacted_before_label"),
        "status": status,
    }

    lead_id, is_duplicate = save_lead(lead)
    lead["id"] = lead_id

    if not is_duplicate:
        await push_to_integrations(lead)
        await notify_admins(message.bot, lead)
    elif NOTIFY_ON_DUPLICATE:
        await notify_admins(message.bot, lead)

    await state.clear()

    if is_duplicate:
        await message.answer("Спасибо! Мы уже получили заявку с этим номером и скоро свяжемся.")
        return

    await message.answer(
        "Спасибо! Мы получили вашу заявку и свяжемся с вами в ближайшее время."
    )


async def notify_admins(bot: Bot, lead: dict) -> None:
    if not ADMIN_IDS:
        return
    text = format_lead_message(lead)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logging.exception("Failed to notify admin %s", admin_id)


async def run_bot() -> None:
    setup_logging()
    init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    logging.info("Lead bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_bot())
