import subprocess
import csv
import re
import os

# --- Configuration ---
STREAM_BINARY = "./stream"

# P-core vCPUs (physical cores with 2 vCPUs each)
P_CORES = [(0,1), (2,3), (4,5), (6,7)]  # adjust if different

# Thread range
MIN_THREADS = 2
MAX_THREADS = 16  # adjust to the number of P-core vCPUs

CSV_FILE = "stream_pcore_affinity.csv"

# --- Helper to flatten high-affinity vCPUs ---
def high_affinity_vcpus(num_threads):
    vcpus = []
    t_remaining = num_threads
    for pair in P_CORES:
        for v in pair:
            if t_remaining > 0:
                vcpus.append(v)
                t_remaining -= 1
    return vcpus

# --- Helper to spread threads for low affinity ---
def low_affinity_vcpus(num_threads):
    vcpus = []
    t_remaining = num_threads
    # Take first CPU from each P-core, then second if more threads
    for i in range(2):  # two vCPUs per core
        for pair in P_CORES:
            if t_remaining > 0:
                vcpus.append(pair[i])
                t_remaining -= 1
    return vcpus

# --- Run STREAM and extract Scale ---
def run_stream(vcpus, threads):
    vcpu_str = ",".join(str(v) for v in vcpus)
    env = {"OMP_NUM_THREADS": str(threads), **os.environ}

    result = subprocess.run(
        ["taskset", "-c", vcpu_str, STREAM_BINARY],
        capture_output=True,
        text=True,
        env=env
    ).stdout

    match = re.search(r"Scale:\s+([\d\.]+)", result)
    if match:
        return float(match.group(1))
    else:
        print(f"WARNING: Scale not found for vCPUs {vcpus}, threads={threads}")
        return None

# --- Main routine ---
def main():
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["threads", "perf_high_affinity", "perf_low_affinity"])

        for threads in range(MIN_THREADS, MAX_THREADS + 1):
            high_v = high_affinity_vcpus(threads)
            low_v = low_affinity_vcpus(threads)

            perf_high = run_stream(high_v, threads)
            perf_low = run_stream(low_v, threads)

            print(f"Threads={threads}, High={perf_high}, Low={perf_low}")
            writer.writerow([threads, perf_high, perf_low])

    print(f"Results saved to {CSV_FILE}")

if __name__ == "__main__":
    main()
