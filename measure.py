import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def executeWithTime(filename):
    result = subprocess.run(["/usr/bin/time", "-v",
                             "python", "-m", "solver",
                             f"./tests/{filename}.py"], check=True, text=True, encoding="utf-8", capture_output=True, timeout=600)
    output = result.stdout.strip()
    stats = result.stderr.strip()
    userTime = None
    sysTime = None
    cpuPercent = None
    wallClock = None
    maxResidentSize = None
    for line in stats.splitlines():
        line = line.strip()
        if line.startswith("User time (seconds):"):
            userTime = float(line.split(':')[1].strip())
        if line.startswith("System time (seconds):"):
            sysTime = float(line.split(':')[1].strip())
        if line.startswith("Percent of CPU this job got:"):
            cpuPercent = int(line.split(':')[1].strip().removesuffix("%"))
        if line.startswith("Elapsed (wall clock) time (h:mm:ss or m:ss):"):
            time = line.removeprefix("Elapsed (wall clock) time (h:mm:ss or m:ss): ").strip()
            minute, second = map(float, time.split(":"))
            wallClock = minute * 60 + second
        if line.startswith("Maximum resident set size (kbytes):"):
            maxResidentSize = int(line.split(':')[1])
    print(f"""
time  : {wallClock} s
cpu   : {cpuPercent} %
memory: {maxResidentSize / 1024} MB
""".strip())

    logfile = Path("./logs") / f"{filename}.json"
    logs = []
    if logfile.is_file():
        logs = json.loads(logfile.read_text())
    logs.append({
        "time": str(datetime.now()),
        "userTime": userTime,
        "sysTime": sysTime,
        "cpuPercent": cpuPercent,
        "wallClock": wallClock,
        "maxResidentSize": maxResidentSize,
        "output": output,
        "stats": stats,
    })
    logfile.write_text(json.dumps(logs))


if __name__ == "__main__":
    assert len(sys.argv) == 2, "Please give a test case."
    executeWithTime(sys.argv[1])