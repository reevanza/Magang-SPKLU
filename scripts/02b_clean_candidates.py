"""
Pembersihan lanjutan Himpunan J — membuang entri yang bukan kandidat valid.

Kenapa perlu ini: klaster C (Perkantoran) menangkap banyak "Pos Satpam" /
"Pos Jaga" / "Pos Linmas" / "Pos Kamling" -- ini adalah pos jaga kecil yang
kebetulan ikut ter-tag office=* di OSM (biasanya oleh mapper komunitas untuk
menandai keamanan lingkungan), BUKAN kantor sungguhan tempat aktivitas rutin
harian pengguna EV sesuai definisi di panduan (poin C).

Prasyarat: sudah menjalankan 02_download_candidates.py.

Output: menimpa candidates_J.geojson dan .csv dengan versi yang sudah
dibersihkan dari entri pos jaga/satpam.
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# pola nama yang menandakan pos jaga/keamanan, bukan kantor sungguhan.
# Menangkap semua yang diawali kata "Pos" (Pos Satpam, Pos Keamanan, Pos RT,
# Pos Rukun Warga, Pos Ronda, dst) atau mengandung kata "security"/"satpam"
# di mana pun posisinya (misal "Posco Security ...", "Security RW 02").
# Pengecualian: "Pos Indonesia" (kantor pos resmi) TIDAK dianggap pos jaga.
EXCLUDE_PATTERN = r"(^pos\b(?!.*indonesia))|\bsecurity\b|\bsatpam\b"


def main():
    path_geojson = PROCESSED_DIR / "candidates_J.geojson"
    print("[1/3] Memuat kandidat SPKLU (Himpunan J)...")
    gdf = gpd.read_file(path_geojson)
    print(f"    Total sebelum dibersihkan: {len(gdf)}")

    print("[2/3] Mengidentifikasi entri pos jaga/satpam...")
    is_guard_post = gdf["nama"].astype(str).str.contains(
        EXCLUDE_PATTERN, case=False, regex=True, na=False
    )
    print(f"    {is_guard_post.sum()} entri terindikasi pos jaga/satpam, akan dibuang:")
    print(f"    Contoh nama yang dibuang: {gdf.loc[is_guard_post, 'nama'].dropna().unique()[:10].tolist()}")

    gdf_clean = gdf[~is_guard_post].reset_index(drop=True)

    print("[3/3] Menyimpan hasil...")
    gdf_clean.to_file(path_geojson, driver="GeoJSON")
    gdf_clean.drop(columns="geometry").assign(
        lon=gdf_clean.geometry.x, lat=gdf_clean.geometry.y
    ).to_csv(PROCESSED_DIR / "candidates_J.csv", index=False)

    print(f"\nSelesai. Kandidat final setelah dibersihkan: {len(gdf_clean)}")
    print(gdf_clean["klaster"].value_counts())


if __name__ == "__main__":
    main()
