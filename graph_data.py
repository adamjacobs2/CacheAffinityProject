import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

# Folder containing CSV files
CSV_DIR = "STREAM"
RESULTS_DIR = "results"

# Each kernel has HA vs LA and BASELINE CSV
FILES = {
    "copy":  ("stream_copy_ha_la.csv",  "stream_copy_BASELINE.csv"),
    "scale": ("stream_scale_ha_la.csv", "stream_scale_BASELINE.csv"),
    "add":   ("stream_add_ha_la.csv",   "stream_add_BASELINE.csv"),
    "triad": ("stream_triad_ha_la.csv", "stream_triad_BASELINE.csv"),
}

# --- Load CSV into dataframe ---
def load_csv(path):
    if not os.path.exists(path):
        print(f"[SKIP] Missing file: {path}")
        return None
    return pd.read_csv(path)

# --- Plot all kernels in one figure ---
def plot_all_kernels(files):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, (kernel, (ha_la_file, BASELINE_file)) in enumerate(files.items()):
        ax = axes[idx]

        df_ha_la = load_csv(os.path.join(CSV_DIR, ha_la_file))
        df_BASELINE = load_csv(os.path.join(CSV_DIR, BASELINE_file))

        if df_ha_la is None:
            continue

        # HA vs LA
        threads = df_ha_la['threads'].to_numpy()
        perf_high = df_ha_la['perf_high_affinity'].to_numpy()
        perf_low  = df_ha_la['perf_low_affinity'].to_numpy()
        ax.plot(threads, perf_high, marker='o', linestyle='-',  label='High cache affinity')
        ax.plot(threads, perf_low,  marker='s', linestyle='--', label='Low cache affinity')

        # BASELINE
        if df_BASELINE is not None:
            BASELINE_threads = df_BASELINE['threads'].to_numpy()
            BASELINE_perf    = df_BASELINE['perf'].to_numpy()
            ax.plot(BASELINE_threads, BASELINE_perf, marker='^', linestyle=':', color='gray', label='BASELINE (1 core)')

        ax.set_xlabel('Threads')
        ax.set_ylabel('Performance (MB/s)')
        ax.set_title(f"{kernel.capitalize()}")
        ax.set_xticks(threads)
        ax.grid(True)
        ax.legend()

    plt.suptitle("STREAM Performance — High Affinity, Low Affinity, and BASELINE")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    # Create results folder if missing
    os.makedirs(RESULTS_DIR, exist_ok=True)
    save_path = os.path.join(RESULTS_DIR, "stream_combined_performance.png")
    plt.savefig(save_path)
    print(f"Plot saved to {save_path}")

    plt.show()


def main():
    print("=== STREAM Combined Graph Generator ===")
    plot_all_kernels(FILES)
    print("Done.")

if __name__ == "__main__":
    main()
