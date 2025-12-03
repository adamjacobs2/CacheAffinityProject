import subprocess
import csv
import statistics

# --- Configuration ---
BINARY = "/usr/lib/lmbench/bin/x86_64-linux-gnu/bw_mem"
SIZE = "16M"   # smaller to see cache effects
OP = "rdwr"
THREAD_RANGE = range(2, 33, 2)  # 2, 4, ..., 32 threads

# High-affinity configs
HA_CONFIGS = [
    [0, 1],
    [2, 3],
]

# Low-affinity configs
LA_CONFIGS = [
    [0, 2],
    [1, 3],
]

CSV_FILE = "lmbench_bw_mem_cache_vs_threads.csv"

# ----------------------------
def generate_vcpus(mapping, num_threads):
    return [mapping[i % len(mapping)] for i in range(num_threads)]

def run_bw_mem_perf(vcpus):
    vcpu_str = ",".join(str(v) for v in vcpus)
    perf_cmd = [
        "perf", "stat",
        "-e", "L1-dcache-loads,L1-dcache-load-misses",
        "--", "taskset", "-c", vcpu_str,
        BINARY, "-P", str(len(vcpus)), SIZE, OP
    ]

    result = subprocess.run(perf_cmd, capture_output=True, text=True)

    hits = misses = None
    for line in result.stderr.splitlines():
        if "L1-dcache-loads" in line:
            parts = line.strip().split()
            if parts[0].replace(',', '').isdigit():
                hits = int(parts[0].replace(',', ''))
        elif "L1-dcache-load-misses" in line:
            parts = line.strip().split()
            if parts[0].replace(',', '').isdigit():
                misses = int(parts[0].replace(',', ''))

    hit_rate = hits / (hits + misses) if hits is not None and misses is not None else None
    return hit_rate

# ----------------------------
def main():
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["threads", "perf_high_affinity", "perf_low_affinity"])

        for threads in THREAD_RANGE:
            # --- High-affinity ---
            ha_results = []
            for ha_map in HA_CONFIGS:
                # repeat mapping to cover all threads
                vcpus = generate_vcpus(ha_map, threads)
                rate = run_bw_mem_perf(vcpus)
                if rate is not None:
                    ha_results.append(rate)
            perf_high = statistics.mean(ha_results) if ha_results else None

            # --- Low-affinity ---
            la_results = []
            for la_map in LA_CONFIGS:
                vcpus = generate_vcpus(la_map, threads)
                rate = run_bw_mem_perf(vcpus)
                if rate is not None:
                    la_results.append(rate)
            perf_low = statistics.mean(la_results) if la_results else None

            print(f"Threads={threads}, HA={perf_high:.3f}, LA={perf_low:.3f}")
            writer.writerow([threads, perf_high if perf_high else "", perf_low if perf_low else ""])

    print(f"\nResults saved to {CSV_FILE}")

# ----------------------------
if __name__ == "__main__":
    main()
