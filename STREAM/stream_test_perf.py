import subprocess
import csv
import re
import os

# --- Configuration ---
STREAM_BINARY = "./stream"
THREAD_RANGE = range(2, 33)  # threads from 2 to 32

# High / Low affinity vCPU mappings for this run
HA_VCPUS = [0, 1]
LA_VCPUS = [0, 2]

CSV_FILE = "stream_perf_cache_affinity.csv"

# --- Helper to generate vCPU list by cycling ---
def generate_vcpus(mapping, num_threads):
    return [mapping[i % len(mapping)] for i in range(num_threads)]

# --- Run STREAM + perf ---
def run_stream_perf(vcpus, threads):
    vcpu_str = ",".join(str(v) for v in vcpus)
    env = {"OMP_NUM_THREADS": str(threads), **os.environ}

    # Run STREAM with perf stat for cache events
    perf_events = [
        "L1-dcache-loads",
        "L1-dcache-load-misses",
        "LLC-loads",
        "LLC-load-misses"
    ]
    cmd = [
        "taskset", "-c", vcpu_str,
        "perf", "stat", "-e", ",".join(perf_events),
        STREAM_BINARY
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    stdout = result.stdout
    stderr = result.stderr  # perf outputs stats to stderr

    # Extract Scale bandwidth
    match = re.search(r"Scale:\s+([\d\.]+)", stdout)
    scale = float(match.group(1)) if match else None

    # Extract perf counters from stderr
    perf_data = {}
    for event in perf_events:
        regex = re.compile(rf"^\s*([\d,]+)\s+{event}", re.MULTILINE)
        m = regex.search(stderr)
        if m:
            perf_data[event] = int(m.group(1).replace(",", ""))
        else:
            perf_data[event] = None

    return scale, perf_data

# --- Main routine ---
def main():
    with open(CSV_FILE, "w", newline="") as f:
        header = [
            "threads",
            "perf_high_affinity",
            "L1_loads_HA", "L1_misses_HA",
            "LLC_loads_HA", "LLC_misses_HA",
            "perf_low_affinity",
            "L1_loads_LA", "L1_misses_LA",
            "LLC_loads_LA", "LLC_misses_LA"
        ]
        writer = csv.writer(f)
        writer.writerow(header)

        for threads in THREAD_RANGE:
            ha_v = generate_vcpus(HA_VCPUS, threads)
            la_v = generate_vcpus(LA_VCPUS, threads)

            perf_high, perf_high_cache = run_stream_perf(ha_v, threads)
            perf_low, perf_low_cache = run_stream_perf(la_v, threads)

            print(f"Threads={threads}, HA={perf_high}, LA={perf_low}")
            row = [
                threads,
                perf_high,
                perf_high_cache["L1-dcache-loads"],
                perf_high_cache["L1-dcache-load-misses"],
                perf_high_cache["LLC-loads"],
                perf_high_cache["LLC-load-misses"],
                perf_low,
                perf_low_cache["L1-dcache-loads"],
                perf_low_cache["L1-dcache-load-misses"],
                perf_low_cache["LLC-loads"],
                perf_low_cache["LLC-load-misses"]
            ]
            writer.writerow(row)

    print(f"Results saved to {CSV_FILE}")

if __name__ == "__main__":
    main()
