"""
Update scope Himpunan J — hanya SPBU Pertamina dan Mall besar/ramai.

Perubahan dari versi sebelumnya:
- Klaster C (Perkantoran) di-DROP seluruhnya
- Klaster A (SPBU): hanya yang bermerek Pertamina resmi (bukan SPBU swasta
  seperti Shell/BP/Vivo, bukan Pertashop, dan bukan "Pertamini" -- yang
  terakhir ini penjual BBM eceran informal, BUKAN Pertamina resmi meski
  namanya mirip)
- Klaster B (Mall): hanya mall besar/ramai berdasarkan whitelist manual,
  bukan seluruh building=retail (yang sebelumnya menangkap minimarket,
  gerai makanan cepat saji, dan toko individual)

Prasyarat: sudah menjalankan 02_download_candidates.py dan 02b_clean_candidates.py.

Output: menimpa candidates_J.geojson dan .csv dengan versi yang sudah
di-filter sesuai scope baru.
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Whitelist mall besar/ramai di Kota Bandung, dikurasi manual berdasarkan
# cross-check beberapa artikel "mall terbesar/terpopuler di Bandung".
# Silakan sesuaikan list ini kalau ada yang perlu ditambah/dikurangi.
MALL_WHITELIST = [
    "23 Paskal Shopping Center", "Balubur Town Square", "Bandung Indah Plaza",
    "Bandung Trade Center", "Bandung Trade Mall", "Braga Citywalk",
    "Cihampelas Walk (CiWalk)", "Istana BEC", "Istana Plaza", "King's Mall",
    "Kosambi Plaza", "Living Plaza", "Mall Festival Citylink", "Metro Indah Mall",
    "Miko Mall", "Paris Van Java", "Plaza Parahyangan", "Riau Junction",
    "Rumah Mode", "Setrasari Mall", "Summarecon Mall Bandung", "Surapati Core",
    "Trans Studio Mall", "Ujungberung Town Square",
]


def main():
    path_geojson = PROCESSED_DIR / "candidates_J.geojson"
    print("[1/4] Memuat kandidat SPKLU (Himpunan J)...")
    gdf = gpd.read_file(path_geojson)
    print(f"    Total sebelum filter scope baru: {len(gdf)}")
    print(f"    {gdf['klaster'].value_counts().to_dict()}")

    print("[2/4] Filter SPBU: hanya Pertamina resmi...")
    spbu = gdf[gdf["klaster"] == "A_SPBU"]
    is_pertamina = spbu["nama"].astype(str).str.contains(
        r"\bpertamina\b", case=False, regex=True, na=False
    )
    spbu_clean = spbu[is_pertamina]
    print(f"    SPBU: {len(spbu)} -> {len(spbu_clean)} (Pertamina resmi saja)")

    print("[3/4] Filter Mall: hanya mall besar/ramai (whitelist)...")
    mall = gdf[gdf["klaster"] == "B_Mall"]
    is_whitelisted = mall["nama"].isin(MALL_WHITELIST)
    mall_clean = mall[is_whitelisted]
    print(f"    Mall: {len(mall)} -> {len(mall_clean)} (whitelist mall besar/ramai)")

    print("[4/4] Menggabungkan hasil (klaster Kantor di-drop seluruhnya)...")
    gdf_final = pd.concat([spbu_clean, mall_clean], ignore_index=True)
    gdf_final = gpd.GeoDataFrame(gdf_final, geometry="geometry", crs=gdf.crs)

    gdf_final.to_file(path_geojson, driver="GeoJSON")
    gdf_final.drop(columns="geometry").assign(
        lon=gdf_final.geometry.x, lat=gdf_final.geometry.y
    ).to_csv(PROCESSED_DIR / "candidates_J.csv", index=False)

    print(f"\nSelesai. Kandidat final (scope baru): {len(gdf_final)}")
    print(gdf_final["klaster"].value_counts())


if __name__ == "__main__":
    main()
