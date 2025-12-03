import subprocess
import csv
import statistics
import os

# --- Configuration ---
BINARY = "/usr/lib/lmbench/bin/x86_64-linux-gnu/bw_mem"  # adjust if needed
SIZE = "1K"   # memory array size
OP = "rdwr"    # bw_mem operation
THREAD_RANGE = range(2, 33, 2)  # number of threads

# High-affinity configs (cores close together)
HA_CONFIGS = [
    [0, 1],
    [2, 3],
]

# Low-affinity configs (cores spread out)
LA_CONFIGS = [
    [0, 2],
    [1, 3],
]

# ----------------------------
# Helper functions
# ----------------------------
def generate_vcpus(mapping, num_threads):
    return [mapping[i % len(mapping)] for i in range(num_threads)]

def run_bw_mem(vcpus, size=SIZE, op=OP):
    vcpu_str = ",".join(str(v) for v in vcpus)
    cmd = ["taskset", "-c", vcpu_str, BINARY, "-P", str(len(vcpus)), size, op]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result)
    # bw_mem output: usually last line contains "size BW"
    for line in result.stderr.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            try:
                bw = float(parts[-1])
                print(bw)
                return bw
            except ValueError:
                continue
    return None

def fmt(x):
    return f"{x:.2f}" if x is not None else "ERR"

# ----------------------------
# Main
# ----------------------------
def main():
    CSV_FILE = "lmbench_bw_mem.csv"
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["threads", "perf_high_affinity", "perf_low_affinity"])

        for threads in THREAD_RANGE:
            # --- High-affinity ---
            ha_results = []
            for ha_map in HA_CONFIGS:
                vcpus = generate_vcpus(ha_map, threads)
                bw = run_bw_mem(vcpus)
                if bw is not None:
                    ha_results.append(bw)
            perf_high = statistics.mean(ha_results) if ha_results else None

            # --- Low-affinity ---
            la_results = []
            for la_map in LA_CONFIGS:
                vcpus = generate_vcpus(la_map, threads)
                bw = run_bw_mem(vcpus)
                if bw is not None:
                    la_results.append(bw)
            perf_low = statistics.mean(la_results) if la_results else None

            print(f"Threads={threads}, HA={fmt(perf_high)}, LA={fmt(perf_low)}")
            writer.writerow([threads, perf_high if perf_high else "", perf_low if perf_low else ""])

    print(f"\n✅ Results saved to {CSV_FILE}")

# ----------------------------
if __name__ == "__main__":
    main()
