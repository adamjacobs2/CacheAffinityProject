#!/usr/bin/env python3
import subprocess
import csv
from pathlib import Path

# -----------------------------
# Configuration
# -----------------------------
LM_DIR = Path("../LMbench/lmbench-3.0-a9/bin/x86_64-linux-gnu")  # LMbench binaries
OUTPUT_CSV = "lmbench_taskset_results.csv"

# Benchmarks to run
BENCHMARKS = ["bw_file_rd", "bw_mem"]

# Cache-affinity / thread configurations
CONFIGS = [
    ("single_thread", [0]),
    ("two_threads", [0,1]),
    ("four_threads", [0,1,2,3]),
    ("eight_threads", [0,1,2,3,4,5,6,7])
]

# File for bw_file_rd
TEST_FILE = "testfile"

# -----------------------------
# Helper function
# -----------------------------
def run_lmbench(benchmark, threads, cores):
    core_list_str = ",".join(str(c) for c in cores)

    if benchmark == "bw_mem":
        # add size and memory operation
        cmd = ["taskset", "-c", core_list_str, str(LM_DIR / benchmark), "-P", str(threads), "1024", "rd"]
    elif benchmark == "bw_file_rd":
        cmd = ["taskset", "-c", core_list_str, str(LM_DIR / benchmark), "-P", str(threads), "1024", "io_only", TEST_FILE]
    else:
        cmd = ["taskset", "-c", core_list_str, str(LM_DIR / benchmark), "-P", str(threads)]

    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Result : ", result.stderr) 
        return result.stderr
    except subprocess.CalledProcessError as e:
        print(f"Error running {benchmark}: {e}")
        return ""

# -----------------------------
# Run and collect results
# -----------------------------
with open(OUTPUT_CSV, "w", newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Benchmark", "Threads", "Cores", "Cache_Sharing", "Output"])

    for desc, cores in CONFIGS:
        threads = len(cores)
        for bench in BENCHMARKS:
            output = run_lmbench(bench, threads, cores)
            writer.writerow([bench, threads, ",".join(map(str, cores)), desc, output.strip()])

print(f"All runs complete. Results saved to {OUTPUT_CSV}")
