import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime
from rich import print

from dataclasses import dataclass


def one(name: str, index: int):
    targetDir = Path("./logs") / name
    os.makedirs(targetDir, exist_ok=True)
    fState = targetDir / f"{index}.json"
    fSolution = targetDir / f"{index}_sol.json"

    def test():
        print(f"Generate {index} for {name}...")
        with fState.open("w+") as f:
            subprocess.run(["python", "-m", "solver", "generate",
                        f"./tests/{name}.py"], stdout=f, check=True)
        print(f"Solve {index} for {name}...")
        with fSolution.open("w+") as f:
            subprocess.run(["python", "-m", "solver", "solve",
                        str(fState.resolve())], stdout=f, check=True)
    
    while True:
        try:
            test()
            break
        except:
            state = fState.read_text()
            bugfile = Path("./bug") / f"{str(int(datetime.now().timestamp()))}.json"
            bugfile.write_text(state)
            print(f"Fail: {index} for {name}, copy to {bugfile}, retry")

    from solver.model.solution import Solution
    data = Solution()
    data.load(json.loads(fSolution.read_text()))
    data.status.display()
    return data.status


def multiple(name: str, limit: int):
    targetDir = Path("./logs") / name
    os.makedirs(targetDir, exist_ok=True)

    TcpuPercent = 0
    TwallClock = 0
    TmaxResidentSize = 0
    TmaxWallClock = 0
    for i in range(limit):
        print(f"----- {i+1} / {limit} -----")
        status = one(name, i+1)

        TcpuPercent += status.cpuPercent
        TwallClock += status.wallClock
        TmaxResidentSize += status.maxResidentSize
        TmaxWallClock = max(TmaxWallClock, status.wallClock)

    print(f"----- RESULT -----")

    print(f"""
time  : (avg) {TwallClock / LIMIT :.4f} s / (max) {TmaxWallClock :.4f} s
cpu   : {TcpuPercent / LIMIT} %
memory: {TmaxResidentSize / LIMIT / 1024 :.4f} MB
""".strip())

    (targetDir / "result.json").write_text(json.dumps({
        "avgTime": TwallClock / LIMIT,
        "maxTime": TmaxWallClock,
        "cpu": TcpuPercent / LIMIT,
        "memory": TmaxResidentSize / LIMIT / 1024,
    }))


if __name__ == "__main__":
    assert len(sys.argv) >= 2, "Please give a test case."
    name = sys.argv[1]
    LIMIT = int(sys.argv[2] if len(sys.argv) > 2 else 10)
    multiple(name, LIMIT)
