# Tambah Grup Ingest Baru (Telegram / BingX)

## Telegram — Grup Baru

1. Edit .env (C:\Users\steph\AppData\Local\hermes\.env):
   TELEGRAM_CHANNEL=<new_channel_id>
2. Jalankan backfill: python backfill.py [max_messages] (signal-ingest/)
3. Parse sinyal: python parse_all.py
4. Cron incremental: tambahkan job di hermes cron (sudah ada vates-nightly-data)

## BingX — Grup Trading (Outlook / Signal Lengkap)

BingX menggunakan format ticker berbeda (USDT perpetual):
- BTCUSDT, ETHUSDT (bukan BTC-USD)
- Perlu normalisasi parser (parser.py saat ini hanya USDT/USDT.P)

Langkah:
1. Tambah dan simpan channel/chat ID BingX ke .env (jika via Telegram bot)
2. Atau: jika grup Discord/Telegram BingX berbeda, buat bot handler baru
3. Perbaiki parser.py: tambah regex BingX ticker (USDT perp / P)
4. Backfill + parse + ingested ke signals.db

## Dokumentasi Lokasi .env & Config

- .env ASLI: $LOCALAPPDATA/hermes/.env (BUKAN ~/.hermes/.env)
- Config: $LOCALAPPDATA/hermes/config.yaml
- Template docs: D:\Vaults\Vault\docs\hermes\
