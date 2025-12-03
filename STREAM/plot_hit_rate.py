import pandas as pd
import matplotlib.pyplot as plt

# --- Load CSV ---
CSV_FILE = "stream_copy_ha_la_perf.csv"  # replace with your actual CSV
df = pd.read_csv(CSV_FILE)

threads = df["threads"]

# --- Plot bandwidth ---
plt.figure(figsize=(10, 6))
plt.plot(threads, df["perf_high_affinity"], marker='o', label="HA bandwidth (MB/s)")
plt.plot(threads, df["perf_low_affinity"], marker='o', label="LA bandwidth (MB/s)")
plt.xlabel("Threads")
plt.ylabel("Bandwidth (MB/s)")
plt.title("STREAM Bandwidth vs Thread Count")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("stream_bandwidth.png")
plt.show()

# --- Plot hit rates ---
plt.figure(figsize=(10, 6))
plt.plot(threads, df["perf_high_affinity_hit_rate"], marker='o', label="HA L1 hit rate")
plt.plot(threads, df["perf_low_affinity_hit_rate"], marker='o', label="LA L1 hit rate")
plt.xlabel("Threads")
plt.ylabel("Hit rate")
plt.title("STREAM L1 Cache Hit Rate vs Thread Count")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig("stream_hit_rate.png")
plt.show()
