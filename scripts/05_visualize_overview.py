"""
Visualisasi ringkasan — menumpuk semua data Tahap 2 jadi satu peta PNG,
buat dilampirkan ke slide/laporan.

Prasyarat: sudah menjalankan 01, 02, 03, 03b, dan 04.

Output:
- data/processed/overview_map.png
"""

import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def main():
    print("[1/5] Memuat graf jaringan jalan (untuk basemap)...")
    G = ox.load_graphml(PROCESSED_DIR / "bandung_drive_utm48s.graphml")
    edges = ox.graph_to_gdfs(G, nodes=False).to_crs("EPSG:4326")

    print("[2/5] Memuat titik permintaan (Himpunan I)...")
    demand = gpd.read_file(PROCESSED_DIR / "demand_points_I.geojson")

    print("[3/5] Memuat kandidat SPKLU (Himpunan J)...")
    candidates = gpd.read_file(PROCESSED_DIR / "candidates_J.geojson")

    print("[4/5] Memuat ground truth SPKLU...")
    ground_truth = gpd.read_file(PROCESSED_DIR / "ground_truth_spklu.geojson")

    print("[5/5] Menggambar peta gabungan...")
    fig, ax = plt.subplots(figsize=(12, 12), dpi=150)

    edges.plot(ax=ax, color="#DDDDDD", linewidth=0.4, zorder=1)
    demand.plot(ax=ax, color="#A8D5BA", markersize=3, alpha=0.5, zorder=2,
                label=f"Titik Permintaan / Himpunan I ({len(demand)})")
    candidates.plot(ax=ax, color="#2E86AB", markersize=14, alpha=0.8, zorder=3,
                     label=f"Kandidat SPKLU / Himpunan J ({len(candidates)})")
    ground_truth.plot(ax=ax, color="#E63946", markersize=40, marker="*", zorder=4,
                       label=f"Ground Truth SPKLU ({len(ground_truth)})")

    ax.set_title("Sebaran Data Spasial — Optimasi Lokasi SPKLU Kota Bandung", fontsize=14, fontweight="bold")
    ax.legend(loc="lower left", fontsize=9, frameon=True)
    ax.set_axis_off()

    out_path = PROCESSED_DIR / "overview_map.png"
    fig.savefig(out_path, bbox_inches="tight", facecolor="white")
    print(f"\nSelesai. Peta tersimpan di: {out_path}")


if __name__ == "__main__":
    main()
