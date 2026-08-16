"""
Eksplorasi Metode P-Median — Sensitivity Analysis (Beberapa Nilai p)

Menjawab pertanyaan: "kalau jumlah SPKLU (p) beda-beda, gimana hasilnya?"
Trade-off yang biasa muncul: makin banyak p, makin pendek jarak rata-rata
warga ke SPKLU terdekat -- tapi ada titik "diminishing returns" di mana
nambah p lagi cuma sedikit ningkatin hasilnya.

Matriks jarak dihitung SEKALI SAJA (bagian paling lambat), lalu dipakai
ulang untuk tiap nilai p -- jauh lebih efisien daripada re-run dari nol
untuk tiap p.

Prasyarat: pipeline Tahap 2 lengkap (01-06 termasuk 02c).
"""

import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from spopt.locate import PMedian
import pulp
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

P_VALUES_TO_TEST = [10, 15, 20, 25]  # <-- sesuaikan kalau mau nilai lain
RADIUS_WAJAR_M = 3000


def main():
    print("[1/4] Memuat graf, titik permintaan, dan kandidat...")
    G = ox.load_graphml(PROCESSED_DIR / "bandung_drive_utm48s.graphml")
    demand = pd.read_csv(PROCESSED_DIR / "demand_points_I.csv")
    demand = demand.dropna(subset=["jumlah_penduduk"]).reset_index(drop=True)
    candidates = pd.read_csv(PROCESSED_DIR / "candidates_J.csv")
    print(f"    {len(demand)} titik permintaan, {len(candidates)} kandidat")

    print(f"[2/4] Menghitung matriks jarak (SEKALI SAJA, dipakai ulang untuk semua nilai p)...")
    cost_matrix = np.full((len(demand), len(candidates)), np.nan)
    demand_nodes = demand["nearest_node"].astype(int).values
    for j, cand_node in enumerate(candidates["nearest_node"].astype(int)):
        lengths = nx.single_source_dijkstra_path_length(G, cand_node, weight="length")
        for i, d_node in enumerate(demand_nodes):
            cost_matrix[i, j] = lengths.get(d_node, np.nan)
        if (j + 1) % 20 == 0 or (j + 1) == len(candidates):
            print(f"    ...{j + 1}/{len(candidates)} kandidat selesai")
    cost_matrix = np.nan_to_num(cost_matrix, nan=999_000)

    weights = demand["jumlah_penduduk"].values

    print(f"\n[3/4] Menjalankan P-Median untuk p = {P_VALUES_TO_TEST}...")
    results = []
    for p in P_VALUES_TO_TEST:
        print(f"    Menjalankan p={p}...")
        pmedian = PMedian.from_cost_matrix(cost_matrix=cost_matrix, weights=weights, p_facilities=p)
        solver = pulp.PULP_CBC_CMD(msg=False)
        pmedian = pmedian.solve(solver)

        selected_idx = [j for j, val in enumerate(pmedian.fac2cli) if len(val) > 0]
        total_dist = pmedian.problem.objective.value()
        mean_dist = total_dist / weights.sum()

        # jarak tiap demand ke SPKLU terpilih TERDEKAT (reuse cost_matrix, tanpa hitung ulang graf)
        min_dist_per_demand = cost_matrix[:, selected_idx].min(axis=1)
        max_dist = min_dist_per_demand.max()
        pct_jauh = (min_dist_per_demand > RADIUS_WAJAR_M).mean() * 100

        results.append({
            "p": p,
            "total_jarak_berbobot": total_dist,
            "jarak_rata2_per_orang_m": mean_dist,
            "jarak_median_m": np.median(min_dist_per_demand),
            "jarak_terjauh_m": max_dist,
            "persen_titik_jauh_dari_3km": pct_jauh,
        })
        print(f"        -> rata-rata: {mean_dist:.0f}m, terjauh: {max_dist:.0f}m, >3km: {pct_jauh:.1f}%")

    results_df = pd.DataFrame(results)

    print("\n[4/4] RINGKASAN PERBANDINGAN:")
    print(results_df.round(1).to_string(index=False))
    results_df.to_csv(PROCESSED_DIR / "pmedian_sensitivity_comparison.csv", index=False)
    print(f"\nTabel tersimpan di: {PROCESSED_DIR / 'pmedian_sensitivity_comparison.csv'}")

    # ============================================================
    # Grafik trade-off: p vs jarak rata-rata (kurva diminishing returns)
    # ============================================================
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    ax1.plot(results_df["p"], results_df["jarak_rata2_per_orang_m"], marker="o", color="#028090", linewidth=2)
    ax1.set_xlabel("Jumlah SPKLU (p)")
    ax1.set_ylabel("Jarak rata-rata per orang (meter)")
    ax1.set_title("Trade-off: Jumlah SPKLU vs Jarak Rata-rata")
    ax1.grid(alpha=0.3)

    ax2.plot(results_df["p"], results_df["persen_titik_jauh_dari_3km"], marker="s", color="#E63946", linewidth=2)
    ax2.set_xlabel("Jumlah SPKLU (p)")
    ax2.set_ylabel("% titik permintaan >3km dari SPKLU")
    ax2.set_title("Trade-off: Jumlah SPKLU vs Cakupan Wilayah")
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(PROCESSED_DIR / "pmedian_sensitivity_chart.png", dpi=150, bbox_inches="tight")
    print(f"Grafik tersimpan di: {PROCESSED_DIR / 'pmedian_sensitivity_chart.png'}")


if __name__ == "__main__":
    main()
