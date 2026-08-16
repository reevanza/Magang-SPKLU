"""
Diagnostik Realisme Hasil P-Median

Mengecek 2 hal yang tidak terlihat dari peta saja:
1. Jarak TERJAUH yang harus ditempuh seorang warga ke SPKLU terdekat
   (P-Median cuma optimalin rata-rata, jadi bisa ada outlier yang jauh banget)
2. Kecamatan mana saja yang TIDAK kebagian SPKLU dalam radius wajar
   (indikasi ketimpangan akses / equity issue)

Prasyarat: sudah menjalankan 07_pmedian_real_data.py.
"""

import osmnx as ox
import networkx as nx
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

RADIUS_WAJAR_M = 3000  # asumsi: 3km dianggap "masih wajar" jaraknya ke SPKLU


def main():
    print("[1/4] Memuat graf, hasil P-Median, dan titik permintaan...")
    G = ox.load_graphml(PROCESSED_DIR / "bandung_drive_utm48s.graphml")
    demand = pd.read_csv(PROCESSED_DIR / "demand_points_I.csv")
    demand = demand.dropna(subset=["jumlah_penduduk"]).reset_index(drop=True)
    selected = pd.read_csv(PROCESSED_DIR / "pmedian_selected_facilities.csv")
    print(f"    {len(demand)} titik permintaan, {len(selected)} SPKLU terpilih")

    print("[2/4] Menghitung jarak tiap titik permintaan ke SPKLU terdekat...")
    selected_nodes = selected["nearest_node"].astype(int).tolist()
    demand_nodes = demand["nearest_node"].astype(int).values

    # untuk tiap SPKLU terpilih, hitung jarak ke semua node, ambil yang minimal per demand
    min_dist = np.full(len(demand), np.inf)
    for node in selected_nodes:
        lengths = nx.single_source_dijkstra_path_length(G, node, weight="length")
        dist_to_this = np.array([lengths.get(n, np.inf) for n in demand_nodes])
        min_dist = np.minimum(min_dist, dist_to_this)

    demand["jarak_ke_spklu_terdekat_m"] = min_dist

    print("[3/4] Analisis jarak...")
    print(f"    Jarak rata-rata (weighted): {np.average(min_dist, weights=demand['jumlah_penduduk']):.0f} m")
    print(f"    Jarak median: {np.median(min_dist):.0f} m")
    print(f"    Jarak TERJAUH: {min_dist.max():.0f} m ({min_dist.max()/1000:.1f} km)")
    n_jauh = (min_dist > RADIUS_WAJAR_M).sum()
    pct_jauh = n_jauh / len(demand) * 100
    print(f"    Titik permintaan dengan jarak >{RADIUS_WAJAR_M/1000:.0f}km: {n_jauh} ({pct_jauh:.1f}%)")

    print(f"\n[4/4] Kecamatan yang TIDAK punya SPKLU dalam radius {RADIUS_WAJAR_M/1000:.0f}km...")
    demand_by_kec = demand.groupby("nama_kecamatan").agg(
        jumlah_titik=("jarak_ke_spklu_terdekat_m", "count"),
        jarak_rata2=("jarak_ke_spklu_terdekat_m", "mean"),
        jarak_maks=("jarak_ke_spklu_terdekat_m", "max"),
        total_penduduk=("jumlah_penduduk", "sum"),
    ).sort_values("jarak_rata2", ascending=False)

    print("\n    10 kecamatan dengan akses TERBURUK (jarak rata-rata terjauh ke SPKLU):")
    print(demand_by_kec.head(10).to_string())

    kecamatan_bermasalah = demand_by_kec[demand_by_kec["jarak_rata2"] > RADIUS_WAJAR_M]
    print(f"\n    Total {len(kecamatan_bermasalah)} kecamatan dengan jarak rata-rata >{RADIUS_WAJAR_M/1000:.0f}km")
    print(f"    Total penduduk terdampak: {kecamatan_bermasalah['total_penduduk'].sum():,.0f} jiwa")

    demand.to_csv(PROCESSED_DIR / "demand_with_distance_check.csv", index=False)
    print(f"\nDetail lengkap tersimpan di: {PROCESSED_DIR / 'demand_with_distance_check.csv'}")


if __name__ == "__main__":
    main()
