import subprocess
import csv
from itertools import cycle

# ----------------------------
# Configuration
# ----------------------------
BW_MEM = "/usr/lib/lmbench/bin/x86_64-linux-gnu/bw_mem"
THREAD_RANGE = range(2, 33, 2)  # 2,4,...,32
BUFFER_SIZE = "64M"

HA_CONFIGS = [
    [0, 1],
    [2, 3],
]

LA_CONFIGS = [
    [0, 2],
    [1, 3],
]

CSV_FILE = "lmbench_bw_mem_stream_cache.csv"

# ----------------------------
# Helper functions
# ----------------------------
def generate_vcpu_list(mapping, num_threads):
    """Repeat CPU mapping to match number of threads."""
    return [mapping[i % len(mapping)] for i in range(num_threads)]

def run_bw_mem_with_perf(threads, cpus):
    """
    Run bw_mem pinned to CPUs with -P threads under perf to get
    bandwidth and cache hit rate.
    Returns: (bandwidth_MB_s, hit_rate)
    """
    cpu_str = ",".join(str(c) for c in cpus)

    # Use perf to count L1-dcache-loads and L1-dcache-load-misses
    perf_cmd = [
        "perf", "stat",
        "-e", "L1-dcache-loads,L1-dcache-load-misses",
        "--", "taskset", "-c", cpu_str,
        BW_MEM, "-P", str(threads), BUFFER_SIZE, "rdwr"
    ]

    try:
        result = subprocess.run(perf_cmd, capture_output=True, text=True)
        
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        print(stderr)
        # Parse bandwidth (last token of stdout)
        bw_tokens = stderr.split()
        bandwidth = float(bw_tokens[-1]) if bw_tokens else None

        # Parse perf counters from stderr
        loads, misses = parse_perf_stat(stderr)
        hit_rate = 1.0 - (misses / loads) if loads and misses else None

        

        return bandwidth, hit_rate

    except Exception as e:
        print(f"[ERROR] Running perf on bw_mem: {e}")
        return None, None
def parse_perf_stat(stderr_text):
    """
    Extract L1 cache loads and misses from perf stat output.
    Ignores lines that are not numeric counters.
    """
    loads = misses = None
    for line in stderr_text.splitlines():
        line = line.strip()
        if not line or not line[0].isdigit():
            continue  # skip non-counter lines
        parts = line.split()
        if len(parts) < 2:
            continue
        count_str, event_name = parts[0], parts[1]
        # remove commas from numbers
        try:
            count = int(count_str.replace(",", ""))
        except ValueError:
            continue
        if "L1-dcache-loads" in event_name:
            loads = count
        elif "L1-dcache-load-misses" in event_name:
            misses = count
    return loads, misses


# ----------------------------
# Main
# ----------------------------
def main():
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "threads",
            "perf_high_affinity",
            "perf_low_affinity",
            "perf_high_affinity_hit_rate",
            "perf_low_affinity_hit_rate"
        ])

        for threads in THREAD_RANGE:
            # --- High-affinity ---
            ha_bw_results = []
            ha_hit_results = []
            for ha_map in HA_CONFIGS:
                vcpus = generate_vcpu_list(ha_map, threads)
                bw, hit = run_bw_mem_with_perf(threads, vcpus)
                if bw is not None:
                    ha_bw_results.append(bw)
                if hit is not None:
                    ha_hit_results.append(hit)
            perf_high = sum(ha_bw_results)/len(ha_bw_results) if ha_bw_results else None
            perf_high_hit = sum(ha_hit_results)/len(ha_hit_results) if ha_hit_results else None

            # --- Low-affinity ---
            la_bw_results = []
            la_hit_results = []
            for la_map in LA_CONFIGS:
                vcpus = generate_vcpu_list(la_map, threads)
                bw, hit = run_bw_mem_with_perf(threads, vcpus)
                if bw is not None:
                    la_bw_results.append(bw)
                if hit is not None:
                    la_hit_results.append(hit)
            perf_low = sum(la_bw_results)/len(la_bw_results) if la_bw_results else None
            perf_low_hit = sum(la_hit_results)/len(la_hit_results) if la_hit_results else None

            print(f"threads={threads}, HA={perf_high:.2f}, LA={perf_low:.2f}, "
                  f"HA_hit={perf_high_hit:.2%}, LA_hit={perf_low_hit:.2%}")
            
            writer.writerow([threads, perf_high, perf_low, perf_high_hit, perf_low_hit])

    print(f"\n✅ Finished! CSV saved to {CSV_FILE}")


if __name__ == "__main__":
    main()
