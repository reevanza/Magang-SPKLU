# SPKLU Bandung — Akuisisi Data Spasial (Tahap 2)

Project ini menjalankan Tahap B, C, D dari Panduan Akuisisi Data Spasial:
jaringan jalan, kandidat lokasi SPKLU (Himpunan J), dan titik permintaan (Himpunan I).

## 1. Setup environment

Kenapa venv? `osmnx`/`geopandas` menarik dependency geospasial (GDAL, PROJ, GEOS)
yang riskan bentrok versi kalau diinstall global. Isolasi per-project lebih aman.

```bash
# di dalam folder spklu_bandung/
python3 -m venv venv

# aktifkan
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows (cmd)
venv\Scripts\Activate.ps1       # Windows (PowerShell)

pip install -r requirements.txt
```

Kalau nanti selesai kerja, keluar dari venv dengan `deactivate`.

## 2. Urutan menjalankan

```bash
cd scripts
python 01_download_road_network.py      # ~2-5 menit, tergantung koneksi
python 02_download_candidates.py        # butuh output step 1
python 03_process_demand_points.py      # butuh output step 1 + CSV BPS (lihat di bawah)
```

### Sebelum step 3: download data populasi manual

Portal opendata.bandung.go.id render datanya lewat JavaScript, jadi tidak bisa
di-download otomatis lewat kode. Lakukan sekali secara manual:

1. Buka https://opendata.bandung.go.id/dataset/jumlah-penduduk-kota-bandung-berdasarkan-kelurahan
2. Download resource-nya sebagai CSV
3. Simpan sebagai `data/raw/penduduk_kelurahan_bandung.csv`

## 3. Struktur output

```
data/
  raw/
    bandung_drive_raw.graphml
    penduduk_kelurahan_bandung.csv      <- kamu taruh manual
  processed/
    bandung_drive_utm48s.graphml        <- Himpunan graf G(V,E) final
    road_network_preview.png            <- cek visual cakupan area
    candidates_J.geojson / .csv         <- Himpunan J
    demand_points_I.geojson / .csv      <- Himpunan I
```

## 4. Catatan penting

- **Ground truth SPKLU eksisting** (untuk validasi) TIDAK di-otomatisasi di sini.
  "Charge.IN" adalah fitur di dalam app PLN Mobile, bukan platform dengan API publik,
  jadi tidak bisa di-scrape langsung. Opsi realistis:
  - cari tag `amenity=charging_station` di OSM buat Bandung (banyak sudah dipetakan komunitas)
  - cek cakupan openchargemap.org (punya API publik, tapi cakupan Indonesia belum tentu lengkap)
  - kompilasi manual dari app PLN Mobile / Google Maps untuk area Bandung
- Kolom `addr_kelurahan` di step 3 sering kosong karena banyak building di OSM
  tidak punya tag `addr:suburb`. Untuk hasil yang lebih rapi, ganti pendekatan
  join populasi dari "match nama kelurahan" menjadi **spatial join** pakai polygon
  batas kelurahan (bisa didapat dari OSM `boundary=administrative` atau shapefile BPS).
