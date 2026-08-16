import pandas as pd
import geopandas as gpd
import osmnx as ox
from pathlib import Path

PROJECT_ROOT = Path.cwd().parent  # sesuaikan kalau perlu
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
UTM_EPSG = 32748

df = pd.read_csv(PROCESSED_DIR / "candidates_J_plus_bumn.csv")
print("Sebelum:", len(df))

# 1. Buang Bandung Trade Mall (BTM) -- sepi, bukan destinasi utama
df = df[df["nama"] != "Bandung Trade Mall"]
print("Setelah buang BTM:", len(df))

# 2. Tambah Tenth Avenue (mall baru, ramai)
titik_baru = pd.DataFrame({
    "nama": ["Tenth Avenue"],
    "lat": [-6.946185241423099],
    "lon": [107.64099958128821],
})

G = ox.load_graphml(PROCESSED_DIR / "bandung_drive_utm48s.graphml")
gdf_baru = gpd.GeoDataFrame(
    titik_baru, geometry=gpd.points_from_xy(titik_baru["lon"], titik_baru["lat"]), crs="EPSG:4326"
).to_crs(f"EPSG:{UTM_EPSG}")

nearest_node, dist = ox.distance.nearest_nodes(
    G, gdf_baru.geometry.x, gdf_baru.geometry.y, return_dist=True
)
gdf_baru["nearest_node"] = nearest_node
gdf_baru["dist_to_node_m"] = dist
gdf_baru["klaster"] = "B_Mall"

gdf_baru_wgs84 = gdf_baru.to_crs("EPSG:4326")
out_baru = gdf_baru_wgs84[["nama", "klaster", "nearest_node", "dist_to_node_m"]].copy()
out_baru["lon"] = gdf_baru_wgs84.geometry.x
out_baru["lat"] = gdf_baru_wgs84.geometry.y

df = pd.concat([df, out_baru], ignore_index=True)

# 3. Simpan
df.to_csv(PROCESSED_DIR / "candidates_J_plus_bumn.csv", index=False)
print("Setelah tambah Tenth Avenue:", len(df))
print(df["klaster"].value_counts())