# metrics_collector.py
import json
import statistics
import pandas as pd
import matplotlib.pyplot as plt
import os

LOG_FILE = "collector.log"
PLOT_DIR = "plots"
RESULTS_HTML = "static/results.html"
TEMPLATE_HTML = "static/base_results_template.html"

os.makedirs(PLOT_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)

def parse_log(logfile=LOG_FILE):
    records = []
    with open(logfile, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                records.append(data)
            except:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 7:
                    try:
                        record = {
                            "timestamp": parts[0],
                            "patient": parts[1],
                            "seq": int(parts[2]),
                            "latency": float(parts[3]),
                            "ecg": int(parts[4]),
                            "bp": int(parts[5]),
                            "spo2": int(parts[6])
                        }
                        records.append(record)
                    except ValueError:
                        continue
    if not records:
        print("No valid records found in log.")
        return None
    df = pd.DataFrame(records)
    df['seq'] = pd.to_numeric(df['seq'], errors='coerce')
    df['latency'] = pd.to_numeric(df['latency'], errors='coerce')
    return df

def compute_metrics(df):
    metrics = {}
    for patient, g in df.groupby("patient"):
        latencies = g['latency'].dropna().tolist()
        seqs = g['seq'].dropna().tolist()
        jitter = [abs(latencies[i]-latencies[i-1]) for i in range(1,len(latencies))] if len(latencies) > 1 else []
        sent_count = max(seqs) if seqs else 0
        received_count = len(seqs)
        pdr = received_count / sent_count if sent_count > 0 else 0
        metrics[patient] = {
            "count": len(latencies),
            "mean_latency": statistics.mean(latencies) if latencies else 0,
            "median_latency": statistics.median(latencies) if latencies else 0,
            "p95_latency": sorted(latencies)[int(0.95*len(latencies))] if latencies else 0,
            "max_latency": max(latencies) if latencies else 0,
            "jitter_mean": statistics.mean(jitter) if jitter else 0,
            "jitter_std": statistics.stdev(jitter) if len(jitter)>1 else 0,
            "PDR": pdr
        }
    return metrics

def plot_metrics(df, metrics):
    if df.empty:
        print("No data to plot.")
        return

    # ----- Latency Histogram -----
    plt.figure(figsize=(8,5))
    plt.hist(df['latency'].dropna(), bins=50, color='skyblue', edgecolor='black')
    plt.title("Message Latency Distribution")
    plt.xlabel("Latency (ms)")
    plt.ylabel("Frequency")
    plt.savefig(os.path.join(PLOT_DIR,"latency_hist.png"))
    plt.close()

    # ----- Latency CDF -----
    plt.figure(figsize=(8,5))
    sorted_latency = sorted(df['latency'].dropna())
    cdf = [i/len(sorted_latency) for i in range(len(sorted_latency))]
    plt.plot(sorted_latency, cdf, marker='.', linestyle='none')
    plt.title("Latency CDF")
    plt.xlabel("Latency (ms)")
    plt.ylabel("CDF")
    plt.grid(True)
    plt.savefig(os.path.join(PLOT_DIR,"latency_cdf.png"))
    plt.close()

    # ----- Jitter Histogram -----
    plt.figure(figsize=(8,5))
    for patient, g in df.groupby("patient"):
        lat = g['latency'].dropna().tolist()
        if len(lat)>1:
            jitter = [abs(lat[i]-lat[i-1]) for i in range(1,len(lat))]
            plt.hist(jitter, bins=50, alpha=0.5, label=patient)
    plt.title("Jitter Distribution per Patient")
    plt.xlabel("Jitter (ms)")
    plt.ylabel("Frequency")
    plt.legend()
    plt.savefig(os.path.join(PLOT_DIR,"jitter_hist.png"))
    plt.close()

    # ----- PDR Bar Chart -----
    patients = list(metrics.keys())
    pdr_values = [metrics[p]["PDR"] for p in patients]
    plt.figure(figsize=(6,4))
    plt.bar(patients, pdr_values, color='green', edgecolor='black')
    plt.title("Packet Delivery Ratio (PDR) per Patient")
    plt.ylabel("PDR")
    plt.ylim(0,1.05)
    plt.savefig(os.path.join(PLOT_DIR,"pdr_bar.png"))
    plt.close()

def print_metrics(metrics):
    print("\n=== Metrics Summary per Patient ===\n")
    for patient, m in metrics.items():
        print(f"Patient {patient}:")
        print(f"  Count: {m['count']}")
        print(f"  Mean Latency: {m['mean_latency']:.2f} ms")
        print(f"  Median Latency: {m['median_latency']:.2f} ms")
        print(f"  95th Percentile Latency: {m['p95_latency']:.2f} ms")
        print(f"  Max Latency: {m['max_latency']:.2f} ms")
        print(f"  Mean Jitter: {m['jitter_mean']:.2f} ms")
        print(f"  Jitter Std Dev: {m['jitter_std']:.2f} ms")
        print(f"  Packet Delivery Ratio (PDR): {m['PDR']:.4f}\n")

def save_results_html(metrics):
    # Use template or simple base HTML
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simulation Results</title>
        <style>
        body { font-family: Arial; background-color: #f5f7fa; padding: 40px; }
        h1 { text-align: center; color: #222; }
        .section { margin-bottom: 40px; }
        .metric-card { background: white; padding: 15px 25px; margin: 15px 0; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        img { display: block; margin: 20px auto; max-width: 80%; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.15); }
        </style>
    </head>
    <body>
        <h1>📊 Simulation Results</h1>
        <div id="summary">
            <!-- METRICS_SUMMARY -->
        </div>
        <div class="section">
            <h2>Generated Plots</h2>
            <img src="../plots/latency_hist.png" alt="Latency Histogram">
            <img src="../plots/latency_cdf.png" alt="Latency CDF">
            <img src="../plots/jitter_hist.png" alt="Jitter Histogram">
            <img src="../plots/pdr_bar.png" alt="PDR Bar Chart">
        </div>
    </body>
    </html>
    """
    html_metrics = ""
    for patient, m in metrics.items():
        html_metrics += f"""
        <div class="metric-card">
            <h3>{patient}</h3>
            <p><b>Mean Latency:</b> {m['mean_latency']:.2f} ms</p>
            <p><b>Median Latency:</b> {m['median_latency']:.2f} ms</p>
            <p><b>95th Percentile Latency:</b> {m['p95_latency']:.2f} ms</p>
            <p><b>Packet Delivery Ratio (PDR):</b> {m['PDR']:.4f}</p>
        </div>
        """
    final_html = template.replace("<!-- METRICS_SUMMARY -->", html_metrics)
    with open(RESULTS_HTML, "w", encoding="utf-8") as f:
     f.write(final_html)

    print(f"Results page generated at {RESULTS_HTML}")

if __name__ == "__main__":
    df = parse_log(LOG_FILE)
    if df is not None:
        metrics = compute_metrics(df)
        print_metrics(metrics)
        plot_metrics(df, metrics)
        save_results_html(metrics)
