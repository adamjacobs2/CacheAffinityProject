import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

# Folder containing CSV files
CSV_DIR = "STREAM"

# Expected STREAM output files
FILES = {
    "copy":  "stream_COPY_ha_la.csv",
    "scale": "stream_SCALE_ha_la.csv",
    "add":   "stream_ADD_ha_la.csv",
    "triad": "stream_TRIAD_ha_la.csv",
}

# --- Load CSV into dataframe ---
def load_csv(path):
    if not os.path.exists(path):
        print(f"[SKIP] Missing file: {path}")
        return None
    return pd.read_csv(path)

# --- Plot HA vs LA for 1 kernel ---
def plot_kernel(kernel, df):
    threads = df['threads'].to_numpy()
    perf_high = df['perf_high_affinity'].to_numpy()
    perf_low  = df['perf_low_affinity'].to_numpy()

    plt.figure(figsize=(9, 5))
    plt.plot(threads, perf_high, marker='o', linestyle='-',  label='High cache affinity')
    plt.plot(threads, perf_low,  marker='s', linestyle='--', label='Low cache affinity')

    plt.xlabel('Threads')
    plt.ylabel('Performance (MB/s)')
    plt.title(f"{kernel.capitalize()} — High vs Low Affinity")
    plt.xticks(threads)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()

# --- Main ---
def main():
    print("=== STREAM Graph Generator ===")
    for kernel, filename in FILES.items():
        path = os.path.join(CSV_DIR, filename)
        df = load_csv(path)
        if df is not None:
            print(f"[OK] Plotting {kernel}")
            plot_kernel(kernel, df)
    print("Done.")

if __name__ == "__main__":
    main()
