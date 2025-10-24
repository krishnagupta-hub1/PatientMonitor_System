import asyncio
import json
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import logging
from collections import defaultdict, deque
import datetime

app = FastAPI()
logging.basicConfig(level=logging.INFO, filename="collector.log", filemode="a",
                    format="%(asctime)s %(levelname)s %(message)s")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# connected dashboards and patients
dashboards = set()
patients = dict()  # websocket -> metadata

# Metrics storage (in-memory)
metrics = defaultdict(lambda: {"sent":0, "received":0, "latencies": []})
# reorder buffer parameters
REORDER_WINDOW_MS = 300
# Keep a small reorder buffer for each patient_id
reorder_buffers = defaultdict(lambda: deque())

def generate_results_html(metrics):
    html = "<html><head><title>Metrics Summary</title></head><body>"
    html += "<h2>Metrics Summary per Patient</h2>\n"
    for pid, data in metrics.items():
        lat_list = data["latencies"]
        if not lat_list:
            continue
        import statistics
        mean_lat = round(statistics.mean(lat_list), 2)
        median_lat = round(statistics.median(lat_list), 2)
        p95_lat = round(sorted(lat_list)[int(0.95 * len(lat_list))], 2)
        max_lat = max(lat_list)
        html += f"<h3>Patient {pid}:</h3>"
        html += "<ul>"
        html += f"<li>Count: {len(lat_list)}</li>"
        html += f"<li>Mean Latency: {mean_lat} ms</li>"
        html += f"<li>Median Latency: {median_lat} ms</li>"
        html += f"<li>95th Percentile Latency: {p95_lat} ms</li>"
        html += f"<li>Max Latency: {max_lat} ms</li>"
        html += "</ul>"
    html += "</body></html>"
    return html

def generate_results_html(metrics):
    html = "<html><head><title>Metrics Summary</title></head><body>"
    html += "<h2>Metrics Summary per Patient</h2>\n"
    for pid, data in metrics.items():
        lat_list = data["latencies"]
        if not lat_list:
            continue
        import statistics
        mean_lat = round(statistics.mean(lat_list), 2)
        median_lat = round(statistics.median(lat_list), 2)
        p95_lat = round(sorted(lat_list)[int(0.95 * len(lat_list))], 2)
        max_lat = max(lat_list)
        html += f"<h3>Patient {pid}:</h3>"
        html += "<ul>"
        html += f"<li>Count: {len(lat_list)}</li>"
        html += f"<li>Mean Latency: {mean_lat} ms</li>"
        html += f"<li>Median Latency: {median_lat} ms</li>"
        html += f"<li>95th Percentile Latency: {p95_lat} ms</li>"
        html += f"<li>Max Latency: {max_lat} ms</li>"
        html += "</ul>"
    html += "</body></html>"
    return html

async def broadcast_to_dashboards(message: dict):
    if dashboards:
        webs = list(dashboards)
        for ws in webs:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logging.warning(f"Failed to send to dashboard: {e}")
                try:
                    dashboards.remove(ws)
                except:
                    pass

@app.websocket("/ws/patient")
async def ws_patient(ws: WebSocket):
    await ws.accept()
    client = f"{ws.client.host}:{ws.client.port}"
    logging.info(f"Patient connected: {client}")
    try:
        while True:
            raw = await ws.receive_text()
            recv_time = int(time.time()*1000)
            try:
                msg = json.loads(raw)
            except Exception:
                try:
                    msg = eval(raw)
                except:
                    logging.error(f"Malformed message: {raw}")
                    continue

            seq = int(msg.get("seq", -1))
            pid = str(msg.get("patient_id", "unknown"))
            t_sent = int(msg.get("timestamp_ms", recv_time))
            payload = msg.get("payload", msg)

            metrics[pid]["received"] += 1
            latency = recv_time - t_sent
            metrics[pid]["latencies"].append(latency)

            ecg = payload.get("ecg", None)
            bp = payload.get("bp", None)
            spo2 = payload.get("spo2", None)

            log_line = f"{datetime.datetime.now()} | {pid} | {seq} | {latency} | {ecg} | {bp} | {spo2}\n"
            with open("collector.log", "a") as f:
                f.write(log_line)

            reorder_buffers[pid].append((seq, t_sent, payload, recv_time))
            to_emit = []
            now_ms = recv_time
            while reorder_buffers[pid]:
                s, ts, pl, rcv = reorder_buffers[pid][0]
                if now_ms - rcv >= REORDER_WINDOW_MS:
                    to_emit.append(reorder_buffers[pid].popleft())
                else:
                    break

            for s, ts, pl, rcv in to_emit:
                out = {
                    "patient_id": pid,
                    "seq": s,
                    "timestamp_ms": ts,
                    "recv_time_ms": rcv,
                    "latency_ms": rcv - ts,
                    "payload": pl
                }
                await broadcast_to_dashboards(out)

    except WebSocketDisconnect:
        logging.info(f"Patient disconnected: {client}")
    except Exception as e:
        logging.exception(f"Exception in patient websocket: {e}")

@app.websocket("/ws/dashboard")
async def ws_dashboard(ws: WebSocket):
    await ws.accept()
    dashboards.add(ws)
    client = f"{ws.client.host}:{ws.client.port}"
    logging.info(f"Dashboard connected: {client}")
    try:
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        logging.info(f"Dashboard disconnected: {client}")
        dashboards.remove(ws)
    except Exception as e:
        logging.exception(f"Dashboard ws error: {e}")
        try:
            dashboards.remove(ws)
        except:
            pass

@app.get("/")
def index():
    html = """
    <html>
      <head><title>Collector</title></head>
      <body>
        <h3>Collector running. Open the dashboard at <a href='/static/dashboard.html'>/static/dashboard.html</a></h3>
      </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/metrics")
def get_metrics():
    result = {}
    for pid, d in metrics.items():
        lat_list = d["latencies"]
        if lat_list:
            import statistics
            result[pid] = {
                "sent_estimate": d["sent"],
                "received": d["received"],
                "lat_mean_ms": statistics.mean(lat_list),
                "lat_p95_ms": sorted(lat_list)[int(0.95 * len(lat_list))] if len(lat_list)>0 else None
            }
        else:
            result[pid] = {"sent_estimate": d["sent"], "received": d["received"]}
    return result

# --- New route to serve results.html ---
@app.get("/reports")
def reports():
    html_content = generate_results_html(metrics)
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
