"""
Perbaikan Tahap D — Spatial join titik permintaan ke polygon kelurahan.

Kenapa perlu ini: tag addr:suburb pada building=residential di OSM untuk
Bandung ternyata kosong hampir di semua titik. Batas administratif kelurahan
di OSM sendiri juga TIDAK LENGKAP (cuma 1 dari 151 kelurahan yang ke-tag
admin_level=8), jadi OSM gak bisa dipakai untuk spatial join kelurahan.

Solusi: pakai sumber batas kelurahan khusus Kota Bandung dari GitHub
(tryfatur/geojson-bandung), yang berisi 151 polygon kelurahan lengkap dengan
nama -- cocok dengan jumlah kelurahan asli Kota Bandung.
Sumber: https://github.com/tryfatur/geojson-bandung

Prasyarat: sudah menjalankan 03_process_demand_points.py sebelumnya.

Output: menimpa demand_points_I.geojson dan .csv dengan versi yang sudah
punya kolom nama_kelurahan (hasil spatial join) dan jumlah_penduduk.
"""

import geopandas as gpd
import pandas as pd
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
UTM_EPSG = 32748

KELURAHAN_URL = (
    "https://raw.githubusercontent.com/tryfatur/geojson-bandung/"
    "master/3273-kota-bandung-level-kelurahan.json"
)
KELURAHAN_CACHE = RAW_DIR / "kelurahan_bandung.json"

POPULATION_CSV = RAW_DIR / "penduduk_kelurahan_bandung.csv"
COL_KELURAHAN = "bps_desa_kelurahan"
COL_JUMLAH_PENDUDUK = "jumlah_penduduk"


def get_kelurahan_boundaries():
    if not KELURAHAN_CACHE.exists():
        print("    Mengunduh batas kelurahan Kota Bandung (sekali saja, ~4.3MB)...")
        r = requests.get(KELURAHAN_URL, timeout=60)
        r.raise_for_status()
        KELURAHAN_CACHE.write_bytes(r.content)
    else:
        print("    Memakai cache lokal batas kelurahan yang sudah ada.")
    gdf = gpd.read_file(KELURAHAN_CACHE)
    gdf = gdf.set_crs("EPSG:4326", allow_override=True)
    return gdf[["nama_kelurahan", "nama_kecamatan", "geometry"]]


def main():
    print("[1/4] Memuat batas polygon kelurahan Kota Bandung...")
    kelurahan = get_kelurahan_boundaries()
    print(f"    {len(kelurahan)} polygon kelurahan dimuat.")
    kelurahan = kelurahan.to_crs(f"EPSG:{UTM_EPSG}")

    print("[2/4] Memuat titik permintaan dari hasil step sebelumnya...")
    demand_path = PROCESSED_DIR / "demand_points_I.geojson"
    demand = gpd.read_file(demand_path).to_crs(f"EPSG:{UTM_EPSG}")
    demand = demand.drop(
        columns=[COL_JUMLAH_PENDUDUK, "nama_kelurahan", "nama_kecamatan"], errors="ignore"
    )

    print("[3/4] Spatial join: titik -> polygon kelurahan yang menaunginya...")
    demand = gpd.sjoin(demand, kelurahan, how="left", predicate="within")
    demand = demand.drop(columns=[c for c in ["index_right"] if c in demand.columns])
    n_matched = demand["nama_kelurahan"].notna().sum()
    print(f"    {n_matched}/{len(demand)} titik berhasil dapat nama kelurahan dari spatial join.")

    print("[4/4] Menggabungkan bobot populasi berdasarkan hasil spatial join...")
    if not POPULATION_CSV.exists():
        print(f"    File {POPULATION_CSV} tidak ditemukan, lewati join populasi.")
    else:
        pop = pd.read_csv(POPULATION_CSV)
        sort_cols = [c for c in ["tahun", "semester"] if c in pop.columns]
        pop_latest = (
            pop.sort_values(sort_cols)
            .groupby(COL_KELURAHAN, as_index=False)
            .last()[[COL_KELURAHAN, COL_JUMLAH_PENDUDUK]]
        )
        pop_latest["_key"] = (
            pop_latest[COL_KELURAHAN].str.strip().str.upper().str.replace(" ", "", regex=False)
        )
        demand["_key"] = (
            demand["nama_kelurahan"].astype(str).str.strip().str.upper().str.replace(" ", "", regex=False)
        )
        demand = demand.merge(
            pop_latest[["_key", COL_JUMLAH_PENDUDUK]], on="_key", how="left"
        ).drop(columns="_key")
        n_weighted = demand[COL_JUMLAH_PENDUDUK].notna().sum()
        print(f"    {n_weighted}/{len(demand)} titik berhasil dapat bobot populasi.")

        unmatched = (
            demand.loc[demand[COL_JUMLAH_PENDUDUK].isna() & demand["nama_kelurahan"].notna(),
                       "nama_kelurahan"].unique()
        )
        if len(unmatched) > 0:
            print(f"    Nama kelurahan yang tidak ketemu match di CSV BPS (cek ejaan):")
            print(f"    {list(unmatched)}")

    demand_wgs84 = demand.to_crs("EPSG:4326")
    demand_wgs84.to_file(PROCESSED_DIR / "demand_points_I.geojson", driver="GeoJSON")
    demand_wgs84.drop(columns="geometry").assign(
        lon=demand_wgs84.geometry.x, lat=demand_wgs84.geometry.y
    ).to_csv(PROCESSED_DIR / "demand_points_I.csv", index=False)

    print(f"\nSelesai. File demand_points_I diperbarui di {PROCESSED_DIR}/")


if __name__ == "__main__":
    main()
