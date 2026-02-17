# Mortgage Lead Bot (универсальный лидогенератор)

Телеграм-бот для сбора и квалификации high-ticket лидов (ипотека, недвижимость, юр. услуги и т.д.)
с автоматической сегментацией, отправкой в CRM/Google Sheets и уведомлением менеджера.

## Быстрый старт

1. Установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Создайте `.env` по примеру `.env.example` и заполните:

- `BOT_TOKEN` — токен бота от BotFather
- `ADMIN_IDS` — Telegram ID админов через запятую
- `NICHE_NAME` — название ниши (например, `Ипотека`)
- `CRM_WEBHOOK_URL` — webhook CRM (опционально)
- `GOOGLE_SHEETS_WEBHOOK_URL` — webhook для Google Sheets (опционально)

3. Запуск:

```bash
python app.py
```

## Команды

- `/start` — запуск сценария
- `/stats` — статистика лидов (админы)
- `/export [YYYY-MM-DD] [YYYY-MM-DD]` — CSV за период (админы)
- `/cancel` — отмена текущего шага

## Интеграции

Бот может отправлять данные в:

- CRM через `CRM_WEBHOOK_URL`
- Google Sheets через `GOOGLE_SHEETS_WEBHOOK_URL`

Обычно для Google Sheets используют Apps Script Web App или Make/Zapier —
укажите URL вебхука, и бот будет отправлять JSON.

Пример Apps Script: `docs/google_sheets_appsscript.js`.

## Несколько ниш

Можно запускать разные ниши через разные env-файлы:

```bash
ENV_FILE=.env.legal python app.py
```

Для юр. ниши используйте шаблон `.env.legal.example`.

## Структура проекта

- `config.py` — настройки ниши и порогов
- `logic.py` — правила сегментации
- `storage.py` — база и интеграции
- `bot.py` — логика бота
- `states.py` — состояния диалога
