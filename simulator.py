# simulator.py
import asyncio, websockets, json, time, argparse, random, logging

logging.basicConfig(level=logging.INFO)

async def run_simulator(uri, patient_id, rate_s=0.1, jitter=0.0, loss_prob=0.0):
    seq = 0
    async with websockets.connect(uri) as ws:
        logging.info(f"Connected simulator {patient_id} -> {uri}")
        while True:
            seq += 1
            now_ms = int(time.time()*1000)
            payload = {
                "ecg": random.randint(60, 100),
                "bp": random.randint(110, 140),
                "spo2": random.randint(90, 100)
            }
            msg = {
                "seq": seq,
                "patient_id": patient_id,
                "timestamp_ms": now_ms,
                "payload": payload
            }
            # Simulate local packet loss
            if random.random() < loss_prob:
                logging.info(f"[{patient_id}] Dropping packet seq={seq} locally (simulated loss)")
            else:
                await ws.send(json.dumps(msg))
            # optional: we could wait for ACK from collector but not implemented here
            # Add rate and jitter
            base_delay = rate_s
            if jitter:
                delay = max(0, base_delay + random.uniform(-jitter, jitter))
            else:
                delay = base_delay
            await asyncio.sleep(delay)

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--uri", default="ws://localhost:8000/ws/patient")
    p.add_argument("--patient-id", default="patient-1")
    p.add_argument("--rate", type=float, default=0.1)   # seconds between sends
    p.add_argument("--jitter", type=float, default=0.0)
    p.add_argument("--loss", type=float, default=0.0)
    return p.parse_args()

if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_simulator(args.uri, args.patient_id, args.rate, args.jitter, args.loss))
