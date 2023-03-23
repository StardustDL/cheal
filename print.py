from pathlib import Path
import json

logs = []

for file in Path("./stats").glob("*.json"):
    _, pod, type, weak = file.stem.split('-')
    item = json.loads(file.read_text())
    logs.append((int(pod), int(type), int(weak), item))

for pod, type, weak, item in sorted(logs):
    print(f"{pod:3d} pods, in {type:3d} types, with {weak:6d} weak connections: {item['avgTime']:.2f} s, {(item['avgMem'] / 1024):.2f} MB, {item['avgCpu']} %")
