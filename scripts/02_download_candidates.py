"""
Tahap C — Akuisisi data kandidat lokasi SPKLU (Himpunan J).

Prasyarat: jalankan 01_download_road_network.py dulu (butuh graf ter-proyeksi).

Output:
- data/processed/candidates_J.geojson
- data/processed/candidates_J.csv
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
import os
from pathlib import Path

PLACE = "Bandung, Indonesia"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = str(PROJECT_ROOT / "data" / "processed")
UTM_EPSG = 32748
SNAP_MAX_DIST_M = 500      # kandidat >500m dari node jalan dibuang
DEDUP_TOLERANCE_M = 50     # radius dedup antar klaster

CLUSTERS = {
    "A_SPBU": {"amenity": "fuel"},
    "B_Mall": {"shop": "mall", "building": "retail"},
    "C_Perkantoran": {"office": True, "building": "office"},
}


def fetch_cluster(name, tags):
    print(f"  Mengambil klaster {name} dengan tag {tags}...")
    try:
        gdf = ox.features_from_place(PLACE, tags)
    except Exception as e:
        print(f"    Kosong / gagal ({e}), skip.")
        return gpd.GeoDataFrame()
    gdf = gdf[gdf.geometry.notnull()].copy()
    # pakai centroid untuk polygon (mall/kantor biasanya berupa building outline)
    gdf["geometry"] = gdf.geometry.centroid
    gdf["klaster"] = name
    gdf["nama"] = gdf.get("name", pd.NA)
    print(f"    Ditemukan {len(gdf)} titik mentah.")
    return gdf[["nama", "klaster", "geometry"]]


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    print("[1/4] Mengunduh graf jalan (buat snapping)...")
    G_path = f"{PROCESSED_DIR}/bandung_drive_utm48s.graphml"
    if not os.path.exists(G_path):
        raise FileNotFoundError(
            "Jalankan 01_download_road_network.py dulu -- graf belum ada."
        )
    G = ox.load_graphml(G_path)

    print("[2/4] Mengekstraksi 3 klaster kandidat dari OSM...")
    all_gdfs = [fetch_cluster(name, tags) for name, tags in CLUSTERS.items()]
    candidates = gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs="EPSG:4326")
    candidates = candidates.to_crs(f"EPSG:{UTM_EPSG}")

    print("[3/4] Snap ke node jalan terdekat & filter jarak...")
    xs = candidates.geometry.x
    ys = candidates.geometry.y
    nearest_nodes, dists = ox.distance.nearest_nodes(G, xs, ys, return_dist=True)
    candidates["nearest_node"] = nearest_nodes
    candidates["dist_to_node_m"] = dists

    before = len(candidates)
    candidates = candidates[candidates["dist_to_node_m"] <= SNAP_MAX_DIST_M].copy()
    print(f"    Buang {before - len(candidates)} titik (>{SNAP_MAX_DIST_M}m dari jaringan). Sisa: {len(candidates)}")

    print("[4/4] Deduplikasi antar klaster (radius {}m)...".format(DEDUP_TOLERANCE_M))
    # dedup sederhana: buffer tiap titik, gabungkan titik yang overlap, ambil 1 per grup
    candidates["geom_buffer"] = candidates.geometry.buffer(DEDUP_TOLERANCE_M / 2)
    dissolved = candidates.set_geometry("geom_buffer").dissolve().explode(index_parts=False)
    # mapping balik: untuk tiap grup dissolve, ambil titik pertama sbg representatif
    candidates["dedup_group"] = gpd.sjoin(
        candidates.set_geometry("geometry"),
        dissolved.reset_index(drop=True).set_geometry("geom_buffer")[["geom_buffer"]].reset_index(),
        predicate="within",
    )["index"].values
    before = len(candidates)
    candidates = candidates.drop_duplicates(subset="dedup_group").copy()
    print(f"    Buang {before - len(candidates)} duplikat. Kandidat final: {len(candidates)}")

    candidates = candidates.drop(columns=["geom_buffer", "dedup_group"]).set_geometry("geometry")
    candidates_wgs84 = candidates.to_crs("EPSG:4326")

    out_geojson = f"{PROCESSED_DIR}/candidates_J.geojson"
    out_csv = f"{PROCESSED_DIR}/candidates_J.csv"
    candidates_wgs84.to_file(out_geojson, driver="GeoJSON")
    candidates_wgs84.drop(columns="geometry").assign(
        lon=candidates_wgs84.geometry.x, lat=candidates_wgs84.geometry.y
    ).to_csv(out_csv, index=False)

    print(f"\nSelesai. {len(candidates)} kandidat tersimpan di:\n  {out_geojson}\n  {out_csv}")
    print(candidates_wgs84["klaster"].value_counts())


if __name__ == "__main__":
    main()
