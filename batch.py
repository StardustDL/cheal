from itertools import product
import json
from pathlib import Path
import subprocess
import traceback

# pods = [200, 500, 1000]
pods = [150]
types = [0.05, 0.1, 0.2]
weaks = [0.05, 0.1, 0.2]
REPEAT = 10


def gen(pod, type, weak):
    name = f"gen-{pod}-{type}-{weak}"
    file = Path(f"./tests/{name}.py")
    file.write_text(f"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from solver.pod import PodManager
    from solver.connection import ConnectionState
    from solver.generator import NetworkGenerator
    pods = PodManager()
    state = ConnectionState(pods)
    gen = NetworkGenerator()

gen.pods(pods, {pod}, {type})
gen.state(state, {weak})
""")
    return name

def solve():
    for pod, type, weak in product(pods, types, weaks):
        type = int(type * pod)
        weak = int(weak * (pod // type) ** 2 * (type * (type - 1) // 2))
        name = gen(pod, type, weak)
        statFile = Path(f"./stats/{name}.json")
        if statFile.is_file():
            continue
        print(f"{name}:")
        for i in range(REPEAT):
            print(f"  repeat {i+1}...")
            try:
                result = subprocess.run(
                    ["python", "measure.py", name], capture_output=True, timeout=660, check=True)
            except Exception as ex:
                subprocess.run(["pkill", "scip"], timeout=60)
                traceback.print_exception(ex)
        logFile = Path(f"./logs/{name}.json")
        if not logFile.is_file():
            print(f"Failed to measure {name}.")
            continue
        logs = json.loads(logFile.read_text())
        if len(logs) > 0:
            avgTime = sum(item["wallClock"] for item in logs) / len(logs)
            avgMem = sum(item["maxResidentSize"] for item in logs) / len(logs)
            avgCpu = sum(item["cpuPercent"] for item in logs) / len(logs)
        else:
            avgTime = 0
            avgMem = 0
            avgCpu = 0
        stats = {
            "avgTime": avgTime,
            "avgMem": avgMem,
            "avgCpu": avgCpu,
        }
        print(f"{name}: {stats}")
        Path(f"./stats/{name}.json").write_text(json.dumps(stats))

def stats():
    for pod, type, weak in product(pods, types, weaks):
        type = int(type * pod)
        weak = int(weak * (pod // type) ** 2 * (type * (type - 1) // 2))
        name = gen(pod, type, weak)
        logFile = Path(f"./logs/{name}.json")
        if not logFile.is_file():
            continue
        logs = json.loads(logFile.read_text())
        n = len(logs)
        if n > 0:
            mid = n // 2
            logs.sort(key=lambda x: float(x["wallClock"]))
            print(name, logs[mid]["wallClock"])
    
solve()