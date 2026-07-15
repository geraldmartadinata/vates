# Vates Core

Bot Telegram analitik kuantitatif saham IHSG.
Dibangun dengan OpenBB, FastAPI, dan SQLAlchemy.

Nama **Vates** — dari bahasa Latin *vates* (peramal/nabi).
Visi jangka panjang: SaaS komersial untuk analitik pasar modal Indonesia.

## Tech Stack

| Lapisan | Teknologi |
|---|---|
| **Data Provider** | OpenBB (Yahoo Finance default) |
| **API Middleware** | FastAPI |
| **User Interface** | Telegram Bot |
| **Database** | SQLAlchemy ORM (SQLite dev → PostgreSQL prod) |

## Struktur Proyek

```
vates-core/
├── main.py            # Entry point FastAPI
├── app/               # Aplikasi: config, routing, bot, ORM
│   ├── config.py      # Pydantic Settings dari .env
│   ├── database.py    # Engine & session SQLAlchemy async
│   ├── models.py      # ORM models
│   ├── schemas.py     # Pydantic request/response
│   ├── router.py      # REST endpoints
│   └── bot.py         # Telegram command handlers
├── services/          # Logika bisnis terisolasi
│   ├── data_engine.py # OpenBB fetcher
│   ├── indicators.py  # Kalkulasi indikator teknikal
│   └── cache.py       # Cache layer via SQLAlchemy
└── tests/             # Unit test (TDD)
```

## Development

```bash
python -m venv .venv
# source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate      # Windows
pip install -r requirements.txt

# Copy environment
cp .env.example .env
# Isi TELEGRAM_BOT_TOKEN dan OPENBB_PERSONAL_ACCESS_TOKEN

# Jalankan dev server
uvicorn main:app --reload
```
