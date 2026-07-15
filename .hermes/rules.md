# Standar Operasional Prosedur (SOP) Mutlak — Vates Core

## SKILL 1: ARCHITECTURE FIRST (BRAINSTORMING & PLANNING)
Sebelum menulis atau mengubah logika inti, dilarang langsung menyentuh kode:
1. Gunakan blok `<scratchpad>` untuk membedah masalah.
2. Susun rencana implementasi dalam micro-tasks.
3. Minta validasi dari Tuan Muda dengan menampilkan struktur folder/arsitektur.
4. Lanjut ke kode HANYA setelah rencana divalidasi.

## SKILL 2: TEST-DRIVEN DEVELOPMENT (TDD) STRICT MODE
Proyek ini berhubungan dengan data finansial yang sensitif terhadap bug. Terapkan Red-Green-Refactor:
1. RED: Tulis unit test (pytest) yang mendefinisikan ekspektasi — akan gagal karena fungsi belum ada.
2. GREEN: Tulis kode produksi minimal agar test lulus.
3. REFACTOR: Rapikan kode tanpa ubah fungsionalitas.
Pengecualian: konfigurasi UI murni atau integrasi bot dasar. Wajib untuk logika OpenBB dan indikator.

## SKILL 3: TERMINAL ERROR RESOLUTION (ANTI-LOOP)
Jika terminal error:
1. DILARANG menjalankan perintah sama berulang kali.
2. DILARANG menebak tanpa dasar.
3. Baca stack trace dan pesan error menyeluruh.
4. Periksa kecocokan versi pustaka.
5. Buat hipotesis baru, eksekusi solusi berbeda. Jika 3x gagal berturut-turut, stop dan laporkan ke Tuan Muda.

## SKILL 4: STRICT MODULARITY (SEPARATION OF CONCERNS)
Pemisahan file ketat:
- `main.py` → entry point / routing FastAPI
- `/services/data_engine.py` → logika pengambilan data OpenBB
- `/services/indicators.py` → kalkulasi indikator teknikal
- `/services/cache.py` → layer cache SQLite via SQLAlchemy
- `/app/bot.py` → handler Telegram Bot
- `/app/router.py` → REST routes
- `/app/models.py` → SQLAlchemy ORM models
- `/app/schemas.py` → Pydantic schemas
- `/app/database.py` → engine & session SQLAlchemy
- `/app/config.py` → konfigurasi dari .env

## SKILL 5: RESOURCE CONSERVATION
Koneksi melalui 9router memiliki limitasi:
1. Exponential backoff saat panggilan API massal.
2. Cache SQLite agar tidak fetch ulang data sama selama fase testing.
3. Batasi baris historis (max 252 hari).
4. Cleanup cache periodik.
