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

pods.pod(*[Pod("sm2", i) for i in range(72)])
pods.configs["sm2"] = PodConfig(3)
pods.pod(*[Pod("nsim", i) for i in range(6)])
pods.configs["nsim"] = PodConfig(1, True)
pods.pod(*[Pod("sbim", i) for i in range(20)])
pods.configs["sbim"] = PodConfig(1, True)
pods.pod(*[Pod("csdb", i) for i in range(26)])
pods.configs["csdb"] = PodConfig(1)
pods.pod(*[Pod("cslb", i) for i in range(8)])
pods.configs["cslb"] = PodConfig(1)
pods.connect("csdb", "sm2")
pods.connect("sbim", "sm2")
pods.connect("nsim", "sm2")
pods.connect("sbim", "cslb")
pods.connect("nsim", "cslb")

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

ports = net.ports()

frenet = net.freeze()

fail = random.choice(ports)
print(f"Fail: {fail}")
frenet.off(fail)

gen = ProbabilityConnectionStateGenerator.fromNetwork(frenet)
state = gen.generate()
submit(state)