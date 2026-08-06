# Vates Core — Agent Context

Bot Telegram analitik kuantitatif saham IHSG. Visi: SaaS analisis pasar modal Indonesia.

## Stack & Command

- Python 3.11+, FastAPI + uvicorn, SQLAlchemy async (SQLite dev → PostgreSQL prod), OpenBB (Yahoo Finance), python-telegram-bot 21.x, pydantic v2
- Test: `python -m pytest -q` (78 test) · Lint: `ruff check .` (config: `ruff.toml`, rule E/F/I/UP/B, line-length 100)
- Run API: `uvicorn main:app --reload` · Scheduler: `python -m services.scheduler` (**proses STANDALONE**, 16:30 WIB — bukan di lifespan)
- Bot polling butuh `updater.start_polling()` eksplisit — jangan hapus tanpa test

## Konvensi Proyek

- TDD strict: RED → GREEN → REFACTOR. Test dulu, implementasi setelah.
- Modularity: logika bisnis di `services/` (satu file satu concern), jangan membesar-besarkan `app/`
- NO MATH FOR AI: hitung pakai pandas/numpy, jangan manual
- Security first: semua kredensial di `.env` (Pydantic Settings di `app/config.py`), tidak ada hardcode
- Config: `ruff.toml` rule set disengaja — jangan tambah rule agresif tanpa diskusi
- Git flow: branch `feat/*`, PR + review, jangan push langsung ke main. CI: pytest + ruff di `feat/*`

## Dokumentasi

- Lengkap: `D:\Vaults\Vault\docs\projects\vates\README.md` (WAJIB dibaca saat mulai sesi)
- Aturan shared: `D:\Vaults\Vault\agent-brain\RULES.md` (TDD, security, git, gaya respons)

## Pitfall

- Scheduler = proses terpisah; jangan dijalankan di dalam FastAPI lifespan
- yfinance/OpenBB bisa rate-limit → cache & backoff (lihat `services/cache.py`)
- Test yang hit network: mock, jangan panggil API asli di test
