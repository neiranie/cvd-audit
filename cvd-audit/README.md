# cvd-audit

Audit otomatis isyarat yang bergantung pada warna untuk Color Vision Deficiency (CVD hasil simulasi) pada situs e-commerce.
Tanpa responden. Semua klaim harus berbunyi "simulated CVD".

## Setup (Windows, PowerShell, Python 3.11/3.12)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
pytest -q tests
```
Setelah semua jalan: `pip freeze > requirements.lock.txt` untuk reproduksibilitas.

## Alur kerja
1. Isi `config/sites.toml`: ganti `CONTACT_EMAIL` dan semua `TODO` dengan URL halaman publik nyata.
2. Crawl: `python -m cvd_audit.crawl --headed` (hasil di `data/raw/`).
3. Audit: `python -m cvd_audit.audit data/raw data/processed --tau 5` (CSV di `data/processed/`).
4. Validasi:
   - `python -m validation.fault_injection` (verifikasi jalur ekstraksi + deteksi)
   - `python validation/pilot_jamil.py <path dataset Jamil & Denes> out.csv` (analisis sekunder rating manusia publik)

## Aturan crawler (jangan dihapus)
robots.txt dipatuhi, user agent mengidentifikasi peneliti, ada jeda antar permintaan, hanya halaman publik tanpa login atau transaksi.
Jika situs memblokir (captcha, 403), crawler berhenti untuk situs itu. Jangan mencoba menghindari blokir; laporkan sebagai batasan.

## Status implementasi (v0)
Sudah: simulasi CVD (Machado 2009 via colour-science), CIEDE2000, kontras WCAG, ekstraksi teks dan tautan-dalam-teks dari DOM,
deteksi "color-only fault" untuk tautan, uji unit, fault injection, crawler sopan.

Belum (TODO sebelum ada klaim di naskah):
- `DEFAULT_TAU = 5.0` adalah PLACEHOLDER. Tentukan dari literatur dan lakukan analisis sensitivitas beberapa tau.
- Uji dengan data referensi Sharma dkk. (34 pasang). Saat ini baru dicek silang dengan colour-science.
- Model simulasi kedua (Brettel/Viénot) untuk analisis ketahanan. Simulasi tritan di Machado hanya pendekatan (peringatan colour-science); utamakan protan dan deutan.
- Isyarat lain: status/badge, pesan error form, state terpilih, seri grafik, kontras komponen UI (WCAG 1.4.11).
- Halaman dengan background-image, teks dalam gambar atau canvas, dan state hover/fokus belum ditangani (ditandai `bg_unknown`).
- Hasil fault injection (precision/recall = 1,0) berlaku untuk jalur ekstraksi karena kebenarannya dibangun dengan metrik yang sama; ini bukan bukti validitas persepsi.
