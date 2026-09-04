# Quick Start: Ingest Grup Telegram Yudo (BingX)

## 1. Tambahkan Channel ID ke .env
Edit file: C:\Users\steph\AppData\Local\hermes\.env
```
TELEGRAM_CHANNEL=<id_grup_yudo>
```

Untuk 2 grup sekaligus, tambahkan baris:
```
TELEGRAM_CHANNEL_YUDO=<id>
TELEGRAM_CHANNEL_BINGX=<id>
```

## 2. Jalankan Backfill (tarik seluruh history)
```
cd D:/project/vates/signal-ingest
python backfill.py [max_messages]  # optional cap
```
- backfill.py: idempotent, aman di-rerun, simpan ke data/signals.db
- Untuk 2 channel: jalankan 2x (satu per channel) atau modify script

## 3. Parse Sinyal
```
python parse_all.py
```
- parser.py (v2) sudah support:
  - Binance: BTCUSDT, ETHUSDT
  - BingX perpetual: HBARUSDT.P, HYPEUSDT.P, ENAUSDT.P, JASMYUSDT.P
  - Plain ticker: BTC -> BTCUSDT
  - XAUUSDT (gold)
- Hasil: kolom ticker, direction, sl_pct, entry, tp, kind='signal'/'chat'

## 4. Cek Hasil
```
python -c "import storage; conn=storage.connect(); print(storage.stats(conn))"
```
- TOTAL=... RANGE=... SIGNAL_KIND=... TOP_TICKERS=...

## 5. Cron Incremental (otomatis tarik pesan baru)
Sudah ada: vates-nightly-data (01:30 WIB, no-agent mode)
Jalankan manual: hermes cron run vates-nightly-data

## Catatan
- Channel "Yudo Trade with us" = existing, ID di .env lama
- Channel "BingX love Yudo" (686 subscriber) = baru, perlu channel ID
- Parser v2 (services/crypto/parser.py) handle .P suffix BingX perpetual
- Ticker format: HBARUSDT.P, HYPEUSDT.P, ENAUSDT.P, JASMYUSDT.P, XAUUSDT