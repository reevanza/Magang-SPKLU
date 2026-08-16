"""
Tahap B — Akuisisi & pemrosesan graf jaringan jalan Kota Bandung.

Output:
- data/raw/bandung_drive_raw.graphml       (graf mentah, WGS84)
- data/processed/bandung_drive_utm48s.graphml  (graf tersimplifikasi + terproyeksi + travel_time)
- data/processed/road_network_preview.png  (visualisasi cepat buat verifikasi cakupan area)
"""

import osmnx as ox
import networkx as nx
import os
from pathlib import Path

# Path selalu relatif ke lokasi project (folder induk dari scripts/), bukan ke
# folder tempat command dijalankan. Jadi aman dijalankan dari mana saja.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = str(PROJECT_ROOT / "data" / "raw")
PROCESSED_DIR = str(PROJECT_ROOT / "data" / "processed")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

PLACE = "Bandung, Indonesia"  # pastikan ini resolve ke Kota Bandung, bukan Kabupaten Bandung
UTM_EPSG = 32748  # UTM Zone 48S


def main():
    print(f"[1/5] Mengunduh drive network untuk: {PLACE}")
    G = ox.graph_from_place(PLACE, network_type="drive")
    ox.save_graphml(G, filepath=f"{RAW_DIR}/bandung_drive_raw.graphml")
    print(f"      Node: {len(G.nodes)}, Edge: {len(G.edges)}")

    print("[2/5] Visualisasi cepat untuk verifikasi cakupan area...")
    fig, ax = ox.plot_graph(
        G, show=False, close=True, node_size=0, edge_linewidth=0.5
    )
    fig.savefig(f"{PROCESSED_DIR}/road_network_preview.png", dpi=200)
    print(f"      Cek file: {PROCESSED_DIR}/road_network_preview.png")
    print("      -> Pastikan bentuknya sesuai batas administratif Kota Bandung sebelum lanjut!")

    print("[3/5] Menyederhanakan topologi graf...")
    # OSMnx men-simplify secara default saat graph_from_place, tapi kita cek konektivitas
    if not nx.is_strongly_connected(G):
        print("      Graf belum strongly connected, mengambil largest strongly connected component...")
        largest_cc = max(nx.strongly_connected_components(G), key=len)
        G = G.subgraph(largest_cc).copy()
    print(f"      Node setelah cleanup: {len(G.nodes)}, Edge: {len(G.edges)}")

    print(f"[4/5] Proyeksi ke UTM Zone 48S (EPSG:{UTM_EPSG})...")
    G_proj = ox.project_graph(G, to_crs=f"EPSG:{UTM_EPSG}")

    print("[5/5] Menambahkan atribut travel_time berdasarkan speed limit OSM...")
    G_proj = ox.add_edge_speeds(G_proj)      # isi speed_kph dari tag maxspeed / default per jenis jalan
    G_proj = ox.add_edge_travel_times(G_proj)  # hitung travel_time (detik) dari length & speed_kph

    out_path = f"{PROCESSED_DIR}/bandung_drive_utm48s.graphml"
    ox.save_graphml(G_proj, filepath=out_path)
    print(f"\nSelesai. Graf final tersimpan di: {out_path}")
    print("Cek checklist F.1 - F.4 di panduan sebelum lanjut ke tahap kandidat SPKLU.")


if __name__ == "__main__":
    main()
