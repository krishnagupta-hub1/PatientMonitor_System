import subprocess, time
NUM = 10
procs = []
for i in range(NUM):
    pid = f"p{i+1}"
    cmd = ["python", "simulator.py", "--patient-id", pid, "--rate", "0.1", "--loss", "0.01"]
    p = subprocess.Popen(cmd)
    procs.append(p)
    time.sleep(0.05)
print(f"Spawned {NUM} simulators")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    for p in procs:
        p.terminate()
