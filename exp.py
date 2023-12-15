from itertools import product
from pathlib import Path
import subprocess
import json
import os

SRC = """
from typing import TYPE_CHECKING
import random

if TYPE_CHECKING:
    from solver.model.connection import ConnectionState
    from solver.model.network import Network, NetworkTopo, FreezedNetwork, Device
    from solver.model.pod import Pod, PodConfig, PodContainer
    from solver.model.solution import Solution, Batch
    from solver.generator import RandomConnectionStateGenerator, ProbabilityConnectionStateGenerator

    def submit(state: ConnectionState): pass

pods = PodContainer()

pods.pod(*[Pod("sm2", i) for i in range(72 * 8)])
pods.configs["sm2"] = PodConfig(3)
pods.pod(*[Pod("nsim", i) for i in range(6 * 8)])
pods.configs["nsim"] = PodConfig(1, True)
pods.pod(*[Pod("sbim", i) for i in range(20 * 8)])
pods.configs["sbim"] = PodConfig(1, True)
pods.pod(*[Pod("csdb", i) for i in range(26 * 8)])
pods.configs["csdb"] = PodConfig(1)
pods.pod(*[Pod("cslb", i) for i in range(8 * 8)])
pods.configs["cslb"] = PodConfig(1)
pods.connect("sm2", "csdb", "sbim", "nsim")
pods.connect("cslb", "sbim", "nsim")

topo = NetworkTopo()
eor = [Device(f"eor-{i}", 2*50) for i in range(2)]
tor = [Device(f"tor-{i}", 2*2+2) for i in range(50)]
host = [Device(f"host-{i}", 2) for i in range(50)]
topo.device(*(eor+tor+host))
for i in range(2):
    for j in range(50):
        for k in range(2):
            topo.cable((eor[i], j*2+k), (tor[j], i*2+k))
for i in range(0, 50, 2):
    t0, t1 = tor[i:i+2]
    h0, h1 = host[i:i+2]
    topo.cable((t0, 0), (h0, 0))
    topo.cable((t0, 1), (h1, 0))
    topo.cable((t1, 0), (h0, 1))
    topo.cable((t1, 1), (h1, 1))

net = Network(topo, pods)
for pod in pods.values():
    net.bind(pod, random.choice(host))
frenet = net.freeze()

ppod = [p.id for p in pods.values()]
phost = [p.id for p in host]
phostPort = sum((p.inames() for p in host), start=[])
ptor = [p.id for p in tor]
ptorPort = sum((p.inames() for p in tor), start=[])
peor = [p.id for p in eor]
peorPort = sum((p.inames() for p in eor), start=[])
pall = net.ports()

FAIL_COUNT = {FAIL_COUNT}
SELECT_PORTS = {SELECT_PORTS}

fail = random.choices(SELECT_PORTS, k=FAIL_COUNT)
frenet.off(*fail)
gen = ProbabilityConnectionStateGenerator.fromNetwork(frenet)
state = gen.generate()
submit(state)
"""

def gensrc(fail_count, select_ports):
    return SRC.replace("{SELECT_PORTS}", select_ports).replace("{FAIL_COUNT}", str(fail_count))

select_ports_choice = ["ppod", "phost", "phostPort", "ptor", "ptorPort", "peorPort", "pall"]
fail_count_choice = list(range(1, 5))

def main():
    for fail, ports in product(fail_count_choice, select_ports_choice):
        name = f"f1k_{fail}_{ports}"
        genfile = Path(f"./tests/{name}.py")
        os.makedirs(genfile.parent, exist_ok=True)
        genfile.write_text(gensrc(fail, ports))
        subprocess.run(["python", "batch.py", name], check=True)

def view():
    for fail, ports in product(fail_count_choice, select_ports_choice):
        name = f"f1k_{fail}_{ports}"
        f = Path(f"./logs/{name}/result.json")
        if not f.exists():
            continue
        data = json.loads(f.read_text())
        print(f"{name:>20}: avg {data['avgTime']:>10.4f}, max {data['maxTime']:>10.4f}, mem {data['memory']:>10.4f}")

if __name__ == "__main__":
    view()
