"""
Eksplorasi Metode P-Median — Data Asli (Himpunan I + Himpunan J)

Beda dari eksperimen toy sebelumnya (01_pmedian_toy_example.py):
- Pakai data ASLI: Himpunan I (titik permintaan + bobot populasi) dan
  Himpunan J (kandidat SPKLU hasil filter Mall besar/ramai + SPBU Pertamina)
- Jarak dihitung lewat JARINGAN JALAN (network distance), bukan garis lurus

Prasyarat: pipeline Tahap 2 sudah lengkap (01 - 06, termasuk 02c).

Cara kerja perhitungan jarak (biar cepat):
Alih-alih menghitung shortest path untuk tiap pasangan (demand, kandidat)
satu-satu (4.477 x 90 = ratusan ribu kali, lambat), untuk tiap KANDIDAT
(cuma ~90) dijalankan sekali "single-source shortest path" ke SEMUA node
lain di graf sekaligus. Jauh lebih efisien.

PENTING: ubah nilai P_FACILITIES di bawah sesuai jumlah SPKLU yang mau
dianalisis (misal 10, 15, 20) -- coba beberapa nilai untuk melihat
trade-off jumlah SPKLU vs total jarak.
"""

import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from spopt.locate import PMedian
import pulp
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

P_FACILITIES = 20  # <-- SESUAIKAN jumlah SPKLU yang mau dipilih


def main():
    print("[1/6] Memuat graf jaringan jalan...")
    G = ox.load_graphml(PROCESSED_DIR / "bandung_drive_utm48s.graphml")
    print(f"    {len(G.nodes)} node, {len(G.edges)} edge")

    print("[2/6] Memuat titik permintaan (Himpunan I)...")
    demand = pd.read_csv(PROCESSED_DIR / "demand_points_I.csv")
    demand = demand.dropna(subset=["jumlah_penduduk"]).reset_index(drop=True)
    print(f"    {len(demand)} titik permintaan (setelah buang yang tidak ada bobot populasi)")

    print("[3/6] Memuat kandidat SPKLU (Himpunan J)...")
    candidates = pd.read_csv(PROCESSED_DIR / "candidates_J.csv")
    print(f"    {len(candidates)} kandidat")

    print(f"[4/6] Menghitung jarak jaringan jalan (dari {len(candidates)} kandidat)...")
    cost_matrix = np.full((len(demand), len(candidates)), np.nan)
    demand_nodes = demand["nearest_node"].astype(int).values

    for j, cand_node in enumerate(candidates["nearest_node"].astype(int)):
        lengths = nx.single_source_dijkstra_path_length(G, cand_node, weight="length")
        for i, d_node in enumerate(demand_nodes):
            cost_matrix[i, j] = lengths.get(d_node, np.nan)
        if (j + 1) % 20 == 0 or (j + 1) == len(candidates):
            print(f"    ...{j + 1}/{len(candidates)} kandidat selesai diproses")

    n_missing = np.isnan(cost_matrix).sum()
    if n_missing > 0:
        print(f"    Peringatan: {n_missing} pasangan tidak terhubung di graf, diisi jarak besar")
        cost_matrix = np.nan_to_num(cost_matrix, nan=999_000)

    print(f"[5/6] Menjalankan model P-Median (memilih {P_FACILITIES} dari {len(candidates)} kandidat)...")
    weights = demand["jumlah_penduduk"].values
    pmedian = PMedian.from_cost_matrix(
        cost_matrix=cost_matrix, weights=weights, p_facilities=P_FACILITIES,
    )
    solver = pulp.PULP_CBC_CMD(msg=False)
    pmedian = pmedian.solve(solver)

    selected_idx = [j for j, val in enumerate(pmedian.fac2cli) if len(val) > 0]
    selected = candidates.iloc[selected_idx].copy()
    selected["jumlah_titik_dilayani"] = [len(pmedian.fac2cli[j]) for j in selected_idx]

    total_dist = pmedian.problem.objective.value()
    mean_dist = total_dist / weights.sum()

    print("\n[6/6] HASIL:")
    print(f"    {len(selected)} lokasi SPKLU terpilih dari {len(candidates)} kandidat:")
    print(selected[["nama", "klaster", "jumlah_titik_dilayani", "lat", "lon"]].to_string(index=False))
    print(f"\n    Total jarak berbobot: {total_dist:,.0f} meter-penduduk")
    print(f"    Rata-rata jarak per penduduk: {mean_dist:.1f} meter")

    selected.to_csv(PROCESSED_DIR / "pmedian_selected_facilities.csv", index=False)
    print(f"\n    Hasil tersimpan di: {PROCESSED_DIR / 'pmedian_selected_facilities.csv'}")

    print("\nMembuat visualisasi...")
    edges = ox.graph_to_gdfs(G, nodes=False).to_crs("EPSG:4326")
    demand_gdf = gpd.GeoDataFrame(demand, geometry=gpd.points_from_xy(demand.lon, demand.lat), crs="EPSG:4326")
    candidates_gdf = gpd.GeoDataFrame(candidates, geometry=gpd.points_from_xy(candidates.lon, candidates.lat), crs="EPSG:4326")
    selected_gdf = candidates_gdf.iloc[selected_idx]

    fig, ax = plt.subplots(figsize=(12, 12), dpi=150)
    edges.plot(ax=ax, color="#DDDDDD", linewidth=0.4, zorder=1)
    demand_gdf.plot(ax=ax, color="#A8D5BA", markersize=3, alpha=0.4, zorder=2,
                     label=f"Titik Permintaan ({len(demand)})")
    candidates_gdf.plot(ax=ax, color="#CCCCCC", markersize=15, zorder=3,
                         label=f"Kandidat tidak terpilih ({len(candidates) - len(selected)})")
    selected_gdf.plot(ax=ax, color="#E63946", markersize=100, marker="*", zorder=4,
                       label=f"SPKLU terpilih ({len(selected)})")

    ax.set_title(f"Hasil P-Median: {len(selected)} Lokasi SPKLU Optimal", fontsize=14, fontweight="bold")
    ax.legend(loc="lower left", fontsize=9)
    ax.set_axis_off()
    fig.savefig(PROCESSED_DIR / "pmedian_result_map.png", bbox_inches="tight", facecolor="white")
    print(f"Peta hasil tersimpan di: {PROCESSED_DIR / 'pmedian_result_map.png'}")


if __name__ == "__main__":
    main()
