"""
Eksplorasi Metode P-Median — Eksperimen Kecil (Toy Example)

Tujuan: memahami cara kerja P-Median sebelum diterapkan ke data
Himpunan I (4.477 titik) dan Himpunan J (90 kandidat) yang sesungguhnya.

Konsep P-Median secara singkat:
- Diberikan sejumlah TITIK PERMINTAAN (demand points) dengan BOBOT
  (misal jumlah penduduk), dan sejumlah KANDIDAT FASILITAS.
- Tujuan: pilih sejumlah p fasilitas dari kandidat, sedemikian rupa
  sehingga TOTAL JARAK BERBOBOT dari semua titik permintaan ke
  fasilitas TERDEKAT yang terpilih menjadi SEMINIMAL mungkin.
- "Berbobot" artinya titik permintaan yang bobotnya besar (misal
  kelurahan padat penduduk) "menarik" fasilitas untuk lebih dekat
  ke situ, dibanding titik yang bobotnya kecil.

Library yang dipakai: spopt (bagian dari PySAL - Python Spatial
Analysis Library), khusus dirancang untuk masalah lokasi-alokasi
spasial seperti P-Median. Solver-nya pakai PuLP (COIN-OR CBC).
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.distance import cdist
from spopt.locate import PMedian
import pulp

np.random.seed(42)  # biar hasilnya konsisten tiap dijalankan (reproducible)

# ============================================================
# 1. Bikin data sintetis kecil dulu (bukan data asli SPKLU)
# ============================================================
print("[1/4] Membuat data sintetis...")

N_DEMAND = 15       # jumlah titik permintaan (analogi: Himpunan I, tapi mini)
N_CANDIDATE = 8      # jumlah kandidat fasilitas (analogi: Himpunan J, tapi mini)
P_FACILITIES = 3     # mau pilih berapa fasilitas dari kandidat itu

# titik permintaan: posisi acak + bobot acak (analogi jumlah penduduk)
demand_xy = np.random.uniform(0, 100, size=(N_DEMAND, 2))
demand_weights = np.random.randint(1000, 20000, size=N_DEMAND)  # analogi jumlah penduduk

# kandidat fasilitas: posisi acak
candidate_xy = np.random.uniform(0, 100, size=(N_CANDIDATE, 2))

print(f"    {N_DEMAND} titik permintaan, {N_CANDIDATE} kandidat fasilitas")
print(f"    Akan memilih {P_FACILITIES} fasilitas terbaik")

# ============================================================
# 2. Hitung matriks jarak (cost matrix)
# ============================================================
print("[2/4] Menghitung matriks jarak antar titik...")
# Catatan: di data asli nanti, jarak ini idealnya dihitung lewat JARINGAN
# JALAN (pakai graf G dari OSMnx + shortest path), bukan garis lurus
# euclidean seperti contoh sederhana ini.
cost_matrix = cdist(demand_xy, candidate_xy, metric="euclidean")
print(f"    Ukuran matriks: {cost_matrix.shape} (demand x candidate)")

# ============================================================
# 3. Jalankan model P-Median
# ============================================================
print("[3/4] Menjalankan model P-Median...")
pmedian = PMedian.from_cost_matrix(
    cost_matrix=cost_matrix,
    weights=demand_weights,
    p_facilities=P_FACILITIES,
)
solver = pulp.PULP_CBC_CMD(msg=False)  # solver open-source bawaan PuLP
pmedian = pmedian.solve(solver)

# ============================================================
# 4. Lihat hasilnya
# ============================================================
print("[4/4] Hasil optimasi:")
selected_facilities = [i for i, val in enumerate(pmedian.fac2cli) if len(val) > 0]
print(f"    Fasilitas terpilih (index kandidat): {selected_facilities}")
print(f"    Total jarak berbobot (objective value): {round(pmedian.problem.objective.value(), 2)}")

for fac_idx in selected_facilities:
    clients = pmedian.fac2cli[fac_idx]
    print(f"    Kandidat #{fac_idx} melayani {len(clients)} titik permintaan: {clients}")

# ============================================================
# Visualisasi sederhana
# ============================================================
fig, ax = plt.subplots(figsize=(8, 8))
ax.scatter(demand_xy[:, 0], demand_xy[:, 1], s=demand_weights / 200,
           c="lightblue", edgecolors="steelblue", label="Titik permintaan (ukuran = bobot)", zorder=2)
ax.scatter(candidate_xy[:, 0], candidate_xy[:, 1], marker="s", s=80,
           c="lightgray", edgecolors="gray", label="Kandidat (tidak terpilih)", zorder=3)
selected_xy = candidate_xy[selected_facilities]
ax.scatter(selected_xy[:, 0], selected_xy[:, 1], marker="*", s=400,
           c="red", edgecolors="darkred", label="Fasilitas TERPILIH", zorder=4)

# gambar garis dari tiap demand ke fasilitas yang melayaninya
for fac_idx in selected_facilities:
    for cli_idx in pmedian.fac2cli[fac_idx]:
        ax.plot([demand_xy[cli_idx, 0], candidate_xy[fac_idx, 0]],
                [demand_xy[cli_idx, 1], candidate_xy[fac_idx, 1]],
                "gray", linewidth=0.5, alpha=0.5, zorder=1)

ax.legend(loc="upper right", fontsize=9)
ax.set_title(f"Eksperimen P-Median (p={P_FACILITIES}) — Data Sintetis")
fig.savefig("pmedian_toy_example.png", dpi=150, bbox_inches="tight")
print("\nVisualisasi tersimpan di: pmedian_toy_example.png")
