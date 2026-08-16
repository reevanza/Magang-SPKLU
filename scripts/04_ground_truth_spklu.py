"""
Tahap E — Akuisisi data ground truth SPKLU eksisting (untuk validasi).

Catatan penting: Charge.IN (PLN Mobile) TIDAK punya API publik, jadi tidak
bisa diotomasi. Open Charge Map punya API tapi sekarang wajib pakai API key
gratis (daftar di https://openchargemap.org lalu ambil key di menu "My Apps").

Script ini pakai OSM (amenity=charging_station) sebagai sumber utama karena
gratis dan tanpa key. Open Charge Map dipakai sebagai pelengkap opsional
kalau kamu sudah daftar API key -- kalau tidak, bagian itu otomatis dilewati.

Output:
- data/processed/ground_truth_spklu.geojson
- data/processed/ground_truth_spklu.csv
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
import requests
import os
from pathlib import Path

PLACE = "Bandung, Indonesia"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Isi API key di sini kalau sudah daftar di openchargemap.org, atau lewat
# environment variable: set OCM_API_KEY=xxxxx  (Windows: set, bukan export)
OCM_API_KEY = os.environ.get("OCM_API_KEY", "")


UTM_EPSG = 32748
DEDUP_DIST_M = 100  # titik OSM & OCM dalam radius ini dianggap lokasi yang sama


def dedup_cross_source(gdf):
    """Buang duplikat lintas sumber (OSM vs OCM) dalam radius DEDUP_DIST_M.
    Titik OSM diprioritaskan disimpan (karena sudah dipakai di tahap lain),
    titik OCM yang overlap dengan OSM akan dibuang."""
    gdf_utm = gdf.to_crs(f"EPSG:{UTM_EPSG}").copy()
    gdf_utm["_orig_idx"] = gdf_utm.index

    osm_mask = gdf_utm["sumber"] == "OSM"
    osm_points = gdf_utm[osm_mask]
    ocm_points = gdf_utm[~osm_mask]

    if len(osm_points) == 0 or len(ocm_points) == 0:
        return gdf  # tidak ada dua sumber untuk dibandingkan

    osm_union_buffer = osm_points.geometry.buffer(DEDUP_DIST_M).unary_union

    is_duplicate_ocm = ocm_points.geometry.intersects(osm_union_buffer)
    n_dup = is_duplicate_ocm.sum()
    print(f"    {n_dup} titik OCM dibuang karena berimpit (<{DEDUP_DIST_M}m) dengan titik OSM.")

    keep_idx = list(osm_points["_orig_idx"]) + list(ocm_points[~is_duplicate_ocm]["_orig_idx"])
    return gdf.loc[keep_idx].reset_index(drop=True)


def fetch_osm_charging_stations():
    print("[1/2] Mengambil amenity=charging_station dari OSM...")
    try:
        gdf = ox.features_from_place(PLACE, tags={"amenity": "charging_station"})
    except Exception as e:
        print(f"    Gagal / kosong: {e}")
        return gpd.GeoDataFrame(columns=["nama", "sumber", "geometry"])
    gdf = gdf[gdf.geometry.notnull()].copy()
    gdf["geometry"] = gdf.geometry.centroid
    gdf["nama"] = gdf.get("name", pd.NA)
    gdf["operator"] = gdf.get("operator", pd.NA)
    gdf["sumber"] = "OSM"
    print(f"    {len(gdf)} titik ditemukan di OSM.")
    return gdf[["nama", "operator", "sumber", "geometry"]]


def fetch_open_charge_map():
    if not OCM_API_KEY:
        print("[2/2] OCM_API_KEY belum diisi, lewati Open Charge Map.")
        print("      (Opsional: daftar gratis di openchargemap.org kalau mau data pembanding)")
        return gpd.GeoDataFrame(columns=["nama", "operator", "sumber", "geometry"])

    print("[2/2] Mengambil data dari Open Charge Map API...")
    url = "https://api.openchargemap.io/v3/poi/"
    params = {
        "output": "json",
        "countrycode": "ID",
        "latitude": -6.9175,   # pusat Kota Bandung
        "longitude": 107.6191,
        "distance": 15,
        "distanceunit": "KM",
        "maxresults": 500,
        "key": OCM_API_KEY,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    rows = []
    for poi in data:
        addr = poi.get("AddressInfo", {})
        if addr.get("Latitude") is None:
            continue
        rows.append({
            "nama": addr.get("Title"),
            "operator": (poi.get("OperatorInfo") or {}).get("Title"),
            "sumber": "OpenChargeMap",
            "geometry": gpd.points_from_xy([addr["Longitude"]], [addr["Latitude"]])[0],
        })
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    print(f"    {len(gdf)} titik ditemukan di Open Charge Map.")
    return gdf


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    osm_gdf = fetch_osm_charging_stations()
    ocm_gdf = fetch_open_charge_map()

    combined = gpd.GeoDataFrame(
        pd.concat([osm_gdf, ocm_gdf], ignore_index=True), crs="EPSG:4326"
    )

    if len(combined) == 0:
        print("\nTidak ada data ground truth ditemukan dari sumber otomatis.")
        print("Kompilasi manual dari app PLN Mobile / Google Maps diperlukan sebagai pelengkap.")
        return

    print("Dedup titik yang berimpit antar sumber (OSM vs OpenChargeMap)...")
    before = len(combined)
    combined = dedup_cross_source(combined)
    print(f"    Total sebelum dedup: {before}, setelah dedup: {len(combined)}")

    print("Filter wilayah: buang titik yang di luar batas Kota Bandung...")
    kelurahan_cache = PROJECT_ROOT / "data" / "raw" / "kelurahan_bandung.json"
    if kelurahan_cache.exists():
        kelurahan = gpd.read_file(kelurahan_cache).set_crs("EPSG:4326", allow_override=True)
        boundary = kelurahan.to_crs(f"EPSG:{UTM_EPSG}").geometry.unary_union
        combined_utm = combined.to_crs(f"EPSG:{UTM_EPSG}")
        di_dalam = combined_utm.geometry.within(boundary)
        n_luar = (~di_dalam).sum()
        if n_luar > 0:
            print(f"    {n_luar} titik dibuang (di luar Kota Bandung): {combined.loc[~di_dalam, 'nama'].tolist()}")
        combined = combined[di_dalam].reset_index(drop=True)
        print(f"    Sisa setelah filter wilayah: {len(combined)}")
    else:
        print("    File batas kelurahan tidak ditemukan (jalankan 03b dulu) -- filter wilayah dilewati!")

    out_geojson = PROCESSED_DIR / "ground_truth_spklu.geojson"
    out_csv = PROCESSED_DIR / "ground_truth_spklu.csv"
    combined.to_file(out_geojson, driver="GeoJSON")
    combined.drop(columns="geometry").assign(
        lon=combined.geometry.x, lat=combined.geometry.y
    ).to_csv(out_csv, index=False)

    print(f"\nTotal {len(combined)} titik ground truth tersimpan di:\n  {out_geojson}\n  {out_csv}")
    print(combined["sumber"].value_counts())
    print(
        "\nCatatan: cakupan OSM untuk charging station di Indonesia belum tentu lengkap.\n"
        "Disarankan cross-check manual beberapa titik lewat app PLN Mobile / Google Maps\n"
        "sebelum dipakai sebagai ground truth validasi -- catat ini sebagai limitasi di laporan."
    )


if __name__ == "__main__":
    main()
