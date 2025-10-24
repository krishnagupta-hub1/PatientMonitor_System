import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

# Read collector log
# Adjust separator and columns as per your collector.log format
df = pd.read_csv(
    "collector.log",
    sep="|",
    names=["timestamp","patient","seq","latency","ecg","bp","spo2"],
    engine='python'
)

# Convert latency to float
df['latency'] = pd.to_numeric(df['latency'], errors='coerce')

# ----------- Latency Histogram ----------- #
plt.figure(figsize=(8,5))
plt.hist(df['latency'].dropna(), bins=50, color='skyblue', edgecolor='black')
plt.title("Message Latency Distribution")
plt.xlabel("Latency (ms)")
plt.ylabel("Frequency")
plt.savefig("latency_hist.png")
plt.show()

# ----------- Compute PDR per patient ----------- #
# Assuming seq numbers are sequentially increasing starting from 1
pdr_dict = defaultdict(lambda: {"sent":0, "received":0})

for patient, group in df.groupby("patient"):
    received_count = len(group)
    # Estimate sent_count from max seq for that patient
    sent_count = group['seq'].max()
    pdr = received_count / sent_count if sent_count > 0 else 0
    pdr_dict[patient]["sent"] = sent_count
    pdr_dict[patient]["received"] = received_count
    pdr_dict[patient]["pdr"] = pdr

# Bar chart of PDR
patients = list(pdr_dict.keys())
pdr_values = [pdr_dict[p]["pdr"] for p in patients]

plt.figure(figsize=(8,5))
plt.bar(patients, pdr_values, color='lightgreen', edgecolor='black')
plt.title("Packet Delivery Ratio per Patient")
plt.ylabel("PDR")
plt.ylim(0,1.05)
plt.savefig("pdr_bar.png")
plt.show()

# ----------- Jitter (inter-message latency variation) ----------- #
jitter_dict = {}
for patient, group in df.groupby("patient"):
    latencies = group['latency'].dropna().values
    if len(latencies) >= 2:
        # Jitter = std of consecutive differences
        diffs = np.abs(np.diff(latencies))
        jitter_dict[patient] = diffs
    else:
        jitter_dict[patient] = np.array([])

# Plot jitter over time for first patient as example
first_patient = patients[0]
plt.figure(figsize=(10,5))
plt.plot(jitter_dict[first_patient], marker='o', linestyle='-', color='orange')
plt.title(f"Jitter over Time for Patient {first_patient}")
plt.xlabel("Message Index")
plt.ylabel("Jitter (ms)")
plt.savefig("jitter_plot.png")
plt.show()
