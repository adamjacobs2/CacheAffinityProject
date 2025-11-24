import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# Example data
threads = np.array([1, 2, 4, 8, 16, 32])
perf_high = np.array([100, 195, 380, 740, 1370, 2600])
perf_low = np.array([90, 160, 300, 520, 850, 1300])

# Plot performance vs threads
plt.figure(figsize=(9, 5))
plt.plot(threads, perf_high, marker='o', linestyle='-', label='High cache affinity')
plt.plot(threads, perf_low,  marker='s', linestyle='--', label='Low cache affinity')

plt.xlabel('Threads')
plt.ylabel('Performance (ops/sec)')
plt.title('Performance vs Threads — High vs Low Cache Affinity')
plt.xticks(threads)
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()
