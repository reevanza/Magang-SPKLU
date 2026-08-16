"""
Tahap D — Penentuan titik permintaan (Himpunan I).

PENTING - langkah manual sebelum menjalankan script ini:
1. Buka https://opendata.bandung.go.id/dataset/jumlah-penduduk-kota-bandung-berdasarkan-kelurahan
2. Klik tombol download / "Data Awal" pada resource-nya, pilih format CSV.
3. Simpan file hasil download sebagai: data/raw/penduduk_kelurahan_bandung.csv
   (Portalnya render lewat JavaScript, jadi tidak bisa didownload otomatis lewat requests biasa
   -- download manual sekali saja, filenya kecil.)

Output:
- data/processed/demand_points_I.geojson
- data/processed/demand_points_I.csv
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
import os
from pathlib import Path

PLACE = "Bandung, Indonesia"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = str(PROJECT_ROOT / "data" / "processed")
RAW_DIR = str(PROJECT_ROOT / "data" / "raw")
UTM_EPSG = 32748
OUTLIER_MAX_DIST_M = 1000  # buang titik permintaan >1km dari node jalan

POPULATION_CSV = f"{RAW_DIR}/penduduk_kelurahan_bandung.csv"
# sesuaikan nama kolom ini dengan header asli file CSV opendata Bandung
COL_KELURAHAN = "bps_desa_kelurahan"
COL_JUMLAH_PENDUDUK = "jumlah_penduduk"


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    print("[1/5] Mengunduh building footprint (building=residential)...")
    buildings = ox.features_from_place(PLACE, tags={"building": "residential"})
    buildings = buildings[buildings.geometry.notnull()].copy()
    print(f"    {len(buildings)} poligon ditemukan.")

    print("[2/5] Ekstraksi centroid...")
    buildings = buildings.to_crs(f"EPSG:{UTM_EPSG}")
    demand = gpd.GeoDataFrame(geometry=buildings.geometry.centroid, crs=f"EPSG:{UTM_EPSG}")
    demand["addr_kelurahan"] = buildings.get("addr:suburb", pd.NA)

    print("[3/5] Snap ke node jalan terdekat...")
    G = ox.load_graphml(f"{PROCESSED_DIR}/bandung_drive_utm48s.graphml")
    xs, ys = demand.geometry.x, demand.geometry.y
    nearest_nodes, dists = ox.distance.nearest_nodes(G, xs, ys, return_dist=True)
    demand["nearest_node"] = nearest_nodes
    demand["dist_to_node_m"] = dists

    before = len(demand)
    demand = demand[demand["dist_to_node_m"] <= OUTLIER_MAX_DIST_M].copy()
    print(f"    Buang {before - len(demand)} outlier (>{OUTLIER_MAX_DIST_M}m). Sisa: {len(demand)}")

    print("[4/5] Menggabungkan bobot populasi dari data BPS/opendata Bandung...")
    if not os.path.exists(POPULATION_CSV):
        print(f"    File {POPULATION_CSV} belum ada -- lewati join populasi.")
        print("    Ikuti instruksi download manual di docstring script ini, lalu jalankan ulang.")
        demand["jumlah_penduduk"] = pd.NA
    else:
        pop = pd.read_csv(POPULATION_CSV)
        sort_cols = [c for c in ["tahun", "semester"] if c in pop.columns]
        pop_latest = (
            pop.sort_values(sort_cols)
            .groupby(COL_KELURAHAN, as_index=False)
            .last()[[COL_KELURAHAN, COL_JUMLAH_PENDUDUK]]
        )
        pop_latest["_key"] = pop_latest[COL_KELURAHAN].str.strip().str.upper()
        demand["_key"] = demand["addr_kelurahan"].astype(str).str.strip().str.upper()
        demand = demand.merge(
            pop_latest[["_key", COL_JUMLAH_PENDUDUK]],
            on="_key",
            how="left",
        ).drop(columns="_key")
        n_missing = demand[COL_JUMLAH_PENDUDUK].isna().sum()
        print(f"    {n_missing} titik tidak dapat bobot (nama kelurahan tidak match / tag OSM kosong).")
        print("    -> Ini normal, banyak building OSM tidak punya tag addr:suburb.")
        print("       Alternatif: spatial join pakai polygon batas kelurahan, bukan match nama.")

    print("[5/5] Menyimpan hasil...")
    demand_wgs84 = demand.to_crs("EPSG:4326")
    demand_wgs84.to_file(f"{PROCESSED_DIR}/demand_points_I.geojson", driver="GeoJSON")
    demand_wgs84.drop(columns="geometry").assign(
        lon=demand_wgs84.geometry.x, lat=demand_wgs84.geometry.y
    ).to_csv(f"{PROCESSED_DIR}/demand_points_I.csv", index=False)

    print(f"\nSelesai. {len(demand)} titik permintaan tersimpan di {PROCESSED_DIR}/")


if __name__ == "__main__":
    main()
