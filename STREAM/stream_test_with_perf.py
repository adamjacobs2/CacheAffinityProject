import subprocess
import csv
import re
import os
import statistics

# --- Configuration ---
STREAM_BINARY = "./stream"
THREAD_RANGE = range(2, 33, 2)  # only even threads

# High-affinity configurations
HA_CONFIGS = [
    [0, 1],
    [2, 3],
]

# Low-affinity configurations
LA_CONFIGS = [
    [0, 2],
    [1, 3],
]

# ----------------------------
# Helper functions
# ----------------------------
def generate_vcpus(mapping, num_threads):
    return [mapping[i % len(mapping)] for i in range(num_threads)]

def run_stream(vcpus, threads, test):
    """Run stream benchmark and parse the output bandwidth."""
    vcpu_str = ",".join(str(v) for v in vcpus)
    env = {"OMP_NUM_THREADS": str(threads), **os.environ}

    result = subprocess.run(
        ["taskset", "-c", vcpu_str, STREAM_BINARY],
        capture_output=True,
        text=True,
        env=env
    ).stdout
    
    print(result)
    match = re.search(rf"{test.capitalize()}:\s+([\d\.]+)", result)
    if match:
        print (float(match.group(1)))
        return float(match.group(1))
    else:
        print(f"WARNING: {test.capitalize()} not found for vCPUs {vcpus}, threads={threads}")
        return None

def run_stream_with_perf(vcpus, threads, test):
    """Run stream under perf to get bandwidth and cache hit rate."""
    vcpu_str = ",".join(str(v) for v in vcpus)
    env = {"OMP_NUM_THREADS": str(threads), **os.environ}
    print("preparing command")
    perf_cmd = [
        "perf", "stat",
        "-e", "L1-dcache-loads,L1-dcache-load-misses",
        "--",
        "taskset", "-c", vcpu_str, STREAM_BINARY
    ]
    result = subprocess.run(perf_cmd, capture_output=True, text=True, env=env)
    print(result)
    # parse bandwidth
    bw = None
    match = re.search(rf"{test.capitalize()}:\s+([\d\.]+)", result.stdout)
    if match:
        bw = float(match.group(1))

    # parse perf counters
    loads = misses = None
    for line in result.stderr.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            count = int(parts[0].replace(",", ""))
        except ValueError:
            continue
        if "L1-dcache-loads" in parts[1]:
            loads = count
        elif "L1-dcache-load-misses" in parts[1]:
            misses = count
    hit_rate = 1.0 - (misses / loads) if loads and misses else None

    return bw, hit_rate

def fmt(x, f="{:.2f}"):
    return f.format(x) if x is not None else "ERR"

# ----------------------------
# Main
# ----------------------------
def main():
    mode = choose_mode()
    test = choose_kernel()
    CSV_FILE = f"stream_{test.lower()}_{mode}_perf.csv"

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        if mode == "BASELINE":
            writer.writerow(["threads", "perf", "perf_hit_rate"])
        else:
            writer.writerow(["threads", "perf_high_affinity", "perf_low_affinity",
                             "perf_high_affinity_hit_rate", "perf_low_affinity_hit_rate"])

        for threads in THREAD_RANGE:
            if mode == "BASELINE":
                vcpus = [0] * threads
                perf, hit = run_stream_with_perf(vcpus, threads, test)
                print(f"Baseline: threads={threads}, perf={fmt(perf)}, hit_rate={fmt(hit, '{:.2%}')}")
                writer.writerow([threads, perf if perf is not None else "", hit if hit is not None else ""])
                continue

            # High-affinity
            ha_bw_results = []
            ha_hit_results = []
            for ha_map in HA_CONFIGS:
                vcpus = generate_vcpus(ha_map, threads)
                bw, hit = run_stream_with_perf(vcpus, threads, test)
                if bw is not None:
                    ha_bw_results.append(bw)
                if hit is not None:
                    ha_hit_results.append(hit)
            perf_high = statistics.mean(ha_bw_results) if ha_bw_results else None
            perf_high_hit = statistics.mean(ha_hit_results) if ha_hit_results else None

            # Low-affinity
            la_bw_results = []
            la_hit_results = []
            for la_map in LA_CONFIGS:
                vcpus = generate_vcpus(la_map, threads)
                bw, hit = run_stream_with_perf(vcpus, threads, test)
                if bw is not None:
                    la_bw_results.append(bw)
                if hit is not None:
                    la_hit_results.append(hit)
            perf_low = statistics.mean(la_bw_results) if la_bw_results else None
            perf_low_hit = statistics.mean(la_hit_results) if la_hit_results else None

            print(f"Threads={threads}, HA={fmt(perf_high)}, LA={fmt(perf_low)}, "
                  f"HA_hit={fmt(perf_high_hit, '{:.2%}')}, LA_hit={fmt(perf_low_hit, '{:.2%}')}")
            
            writer.writerow([
                threads,
                perf_high if perf_high is not None else "",
                perf_low if perf_low is not None else "",
                perf_high_hit if perf_high_hit is not None else "",
                perf_low_hit if perf_low_hit is not None else ""
            ])

    print(f"\n✅ Results saved to {CSV_FILE}")

# ----------------------------
# Helper prompts
# ----------------------------
def choose_mode():
    print("Which mode do you want to test?")
    print("1) HA vs LA")
    print("2) Baseline")
    choice = input("Enter choice (1–2): ").strip()
    mapping = {"1": "ha_la", "2": "BASELINE"}
    return mapping.get(choice, "ha_la")

def choose_kernel():
    print("Which STREAM kernel do you want to test?")
    print("1) Copy\n2) Scale\n3) Add\n4) Triad")
    choice = input("Enter choice (1–4): ").strip()
    mapping = {"1": "COPY", "2": "SCALE", "3": "ADD", "4": "TRIAD"}
    return mapping.get(choice, "TRIAD")

if __name__ == "__main__":
    main()
