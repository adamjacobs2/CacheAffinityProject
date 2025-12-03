import pandas as pd
import matplotlib.pyplot as plt
import os

# Ensure results directory exists
os.makedirs("../../results", exist_ok=True)


cache_file = "lmbench_bw_mem_cache_vs_threads.csv"  # your first dataset
bwfile   = "lmbench_bw_mem.csv"    # your second dataset

# Read CSV files
df_norm = pd.read_csv(cache_file)
df_abs  = pd.read_csv(bwfile)

# ---- Plot normalized performance ----
plt.figure(figsize=(8,5))
plt.plot(df_norm['threads'], df_norm['perf_high_affinity'], marker='o', label='High Affinity')
plt.plot(df_norm['threads'], df_norm['perf_low_affinity'], marker='o', label='Low Affinity')
plt.xlabel('Threads')
plt.ylabel('Cache Hit Rate')
plt.title('LM Bench Cache Hit Rate (rdwr) HA vs LA for 2-32 Threads')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("results/lmbench_cache_results.png")  # save to results folder
plt.show()

# ---- Plot absolute performance ----
plt.figure(figsize=(8,5))
plt.plot(df_abs['threads'], df_abs['perf_high_affinity'], marker='o', label='High Affinity')
plt.plot(df_abs['threads'], df_abs['perf_low_affinity'], marker='o', label='Low Affinity')
plt.xlabel('Threads')
plt.ylabel('Throughput (Mbps)')
plt.title('LMBench throughput (rdwr)')
plt.legend()
plt.savefig("results/lmbench_bw_results.png")
plt.show()
