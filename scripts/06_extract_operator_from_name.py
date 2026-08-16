"""
Pembersihan lanjutan Ground Truth SPKLU — ekstrak brand/operator yang
nyempil di depan kolom nama (format umum dari Open Charge Map: "(Brand) Nama Lokasi").

Prasyarat: sudah menjalankan 04_ground_truth_spklu.py.

Output: menimpa ground_truth_spklu.geojson dan .csv dengan kolom operator
yang lebih lengkap, dan kolom nama yang sudah bersih dari prefix brand.
"""

import geopandas as gpd
import pandas as pd
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

BRAND_PATTERN = re.compile(r"^\((.*?)\)\s*(.*)$")


def extract_brand(row):
    nama = str(row["nama"]) if pd.notna(row["nama"]) else ""
    match = BRAND_PATTERN.match(nama)
    if match:
        brand, sisa_nama = match.group(1).strip(), match.group(2).strip()
        operator_kosong = pd.isna(row["operator"]) or row["operator"] == "(Unknown Operator)"
        new_operator = brand if operator_kosong else row["operator"]
        new_nama = sisa_nama if sisa_nama else nama
        return pd.Series([new_nama, new_operator])
    return pd.Series([row["nama"], row["operator"]])


def main():
    path_geojson = PROCESSED_DIR / "ground_truth_spklu.geojson"
    print("[1/3] Memuat ground truth SPKLU...")
    gdf = gpd.read_file(path_geojson)
    print(f"    Total: {len(gdf)} titik")

    print("[2/3] Mengekstrak brand/operator dari kolom nama...")
    before_unknown = (gdf["operator"].isna() | (gdf["operator"] == "(Unknown Operator)")).sum()
    gdf[["nama", "operator"]] = gdf.apply(extract_brand, axis=1)
    after_unknown = (gdf["operator"].isna() | (gdf["operator"] == "(Unknown Operator)")).sum()
    print(f"    Operator tidak diketahui: {before_unknown} -> {after_unknown}")

    print("[3/3] Menyimpan hasil...")
    gdf.to_file(path_geojson, driver="GeoJSON")
    gdf.drop(columns="geometry").assign(
        lon=gdf.geometry.x, lat=gdf.geometry.y
    ).to_csv(PROCESSED_DIR / "ground_truth_spklu.csv", index=False)

    print("\nSelesai. Ringkasan operator setelah dibersihkan:")
    print(gdf["operator"].value_counts(dropna=False))


if __name__ == "__main__":
    main()
