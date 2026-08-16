# Optimasi Lokasi SPKLU Kota Bandung — Model P-Median

Notebook ini menjalankan seluruh alur optimasi lokasi Stasiun Pengisian Kendaraan Listrik Umum (SPKLU) di Kota Bandung menggunakan model P-Median, dengan bobot demand berbasis estimasi kendaraan listrik roda empat pada penduduk usia 25–60 tahun.

## Model Objektif

$$\min \sum_i\sum_j w_i \, d_{ij} \, x_{ij}$$

dengan:
- $w_i$ = estimasi jumlah EV berbobot demografi usia 25–60 tahun pada kelurahan $i$
- $d_{ij}$ = jarak jaringan jalan dari titik permintaan $i$ ke kandidat lokasi $j$
- $x_{ij}$ = 1 jika permintaan $i$ dilayani fasilitas $j$, 0 jika tidak

Kendala: setiap titik permintaan dilayani tepat satu fasilitas, fasilitas hanya bisa melayani jika dibuka, dan jumlah fasilitas yang dibuka = $p$.

## Struktur Folder

Letakkan notebook di folder `notebooks/`, dengan struktur project sebagai berikut:

```text
spklu_bandung/
├── data/
│   ├── raw/
│   │   ├── Kendaraan Listrik Bdg Raya.xlsx
│   │   ├── jumlah_penduduk_kota_bandung_berdasarkan_kelompok_u_1.xlsx
│   │   ├── penduduk_kelurahan_bandung.csv
│   │   └── kelurahan_bandung.json
│   └── processed/
│       ├── kandidat_J_gabungan_final.csv
│       └── bandung_drive_utm48s.graphml
├── notebooks/
│   └── 04_pmedian_spklu_lengkap_usia_25_60.ipynb
└── outputs/
    └── pmedian_usia_25_60/        # dibuat otomatis oleh notebook
```

## Dependencies

```bash
pip install pulp numpy pandas geopandas networkx osmnx folium openpyxl
```

Kalau `pulp` belum tersedia di kernel, jalankan `%pip install pulp` sekali lalu restart kernel.

Solver ILP yang dipakai: **CBC** (via `PULP_CBC_CMD`, bundled dengan `pulp`).

## Alur Notebook

| # | Tahap | Cell |
|---|---|---|
| 1 | Baca jumlah EV roda empat per wilayah SAMSAT | 4 |
| 2 | Estimasi & distribusi penduduk usia 25–60 dari kecamatan ke kelurahan | 6–8 |
| 3 | Bentuk Himpunan I (titik permintaan per kelurahan + bobot EV) | 8–10 |
| 4 | Baca & bersihkan Himpunan J (kandidat lokasi SPKLU) | 12–14 |
| 5 | Snap I & J ke jaringan jalan, hitung matriks jarak (Dijkstra) | 14–16 |
| 6 | Jalankan model P-Median (ILP, solver CBC) untuk tiap $p$ di `P_SCENARIOS` | 18–20 |
| 7 | Simpan lokasi terpilih, assignment, ringkasan skenario | 22, 26 |
| 8 | Buat peta interaktif (folium) untuk skenario `P_MAP` | 24 |

## Konfigurasi Utama

Di **cell 2** (setup):
```python
P_SCENARIOS = [5, 10, 15, 20]   # daftar nilai p yang mau diuji
```

Di **cell 24** (peta):
```python
P_MAP = 10   # skenario p yang ingin divisualisasikan ke HTML
```

Ubah nilai-nilai ini sebelum re-run kalau mau menambah skenario atau ganti fokus visualisasi peta.

## Cara Menjalankan

1. Pastikan struktur folder & data mentah sudah sesuai (lihat di atas).
2. Jalankan notebook dari cell paling atas secara berurutan (`Run All`), **atau**:
   - Kalau cuma mau ubah daftar skenario `p` tanpa ubah data mentah, cukup edit cell 2 lalu jalankan ulang **cell 2 → 20 → 22 → 26** (variabel `demand`, `candidates`, `distance_matrix` tetap ada di memory kernel selama tidak di-restart).
   - Kalau cuma mau generate ulang peta untuk `p` yang beda, edit `P_MAP` di cell 24 lalu jalankan ulang cell itu saja.
3. Output tersimpan otomatis ke `outputs/pmedian_usia_25_60/`, antara lain:
   - `ringkasan_skenario_pmedian.csv` — ringkasan objective, jarak rata-rata/maksimum, dan waktu solver per skenario $p$
   - `peta_pmedian_p{N}.html` — peta interaktif untuk skenario $p=N$
   - detail lokasi terpilih & assignment per skenario

## Validasi yang Sudah Diperiksa

- Total bobot EV Himpunan I = 7.136 (sama persis dengan sumber data SAMSAT)
- 151 kelurahan lengkap terpadankan ke poligon geografis
- 272 kandidat lokasi unik (dari 282 awal, dideduplikasi berdasarkan snap ke node jalan)
- 0 pasangan jarak tak berhingga (`inf`) pada matriks jarak
- Seluruh skenario `p` mencapai status **Optimal** pada solver CBC

## Catatan Data

- Dua pasang nama kelurahan pada data penduduk vs GeoJSON dipadankan otomatis via fuzzy matching (`difflib.SequenceMatcher`, ambang 0,70) dan telah diverifikasi manual ke sumber resmi (Pemkot Bandung/BPS/Kecamatan): `CIMINCRANG` ↔ `CIMENCRANG`, dan `HUSENSASTRANEGARA` ↔ `HUSEINSASTRANEGARA`.
- Snap ke jaringan jalan menggunakan komponen *strongly connected* terbesar dari graf OSMnx untuk menghindari jarak tak berhingga akibat jalan satu arah yang terisolasi.
