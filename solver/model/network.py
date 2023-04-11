from dataclasses import dataclass, field
from functools import cached_property

from ..algorithms.path import ShortestPathCollector

from .pod import Pod, PodContainer
from ..serialization import Serializable


@dataclass
class Device(Serializable):
    id: str = "device"
    ports: int = field(default=2)

    def iname(self, num: int):
        assert 0 <= num < self.ports
        return f"{self.id}:{num}"

    def inames(self):
        return [self.iname(i) for i in range(self.ports)]


DeviceInterface = tuple[Device, int]


@dataclass
class NetworkTopo(Serializable, dict[str, Device]):
    cables: dict[str, set[str]] = field(default_factory=dict)

    def cable(self, source: DeviceInterface, target: DeviceInterface):
        sW, sI = source
        tW, tI = target
        assert sW.id in self and tW.id in self
        sI = sW.iname(sI)
        tI = tW.iname(tI)
        if sI > tI:
            sI, tI = tI, sI
        if sI not in self:
            self.cables[sI] = set()
        self.cables[sI].add(tI)

    def device(self, *devices: Device):
        for device in devices:
            assert device.id not in self
            self[device.id] = device

    def ports(self):
        return sum((v.inames() for v in self.values()), start=[]) + list(self.keys())


@dataclass
class Network(Serializable):
    topo: NetworkTopo = field(default_factory=NetworkTopo)
    pods: PodContainer = field(default_factory=PodContainer)
    binds: dict[str, str] = field(default_factory=dict)

    def bind(self, pod: Pod, device: Device):
        assert pod.id in self.pods and device.id in self.topo
        self.binds[pod.id] = device.id

    def ports(self):
        return self.topo.ports() + list(self.pods.keys())

    def freeze(self):
        return FreezedNetwork(topo=self.topo, pods=self.pods, binds=self.binds)


@dataclass
class FreezedNetwork(Network):
    weakInts: set[int] = field(default_factory=set)
    id2int: dict[str, int] = field(default_factory=dict, init=False)
    int2id: dict[int, str] = field(default_factory=dict, init=False)
    paths: dict[int, dict[int, list["LinkPath"]]] = field(
        default_factory=dict, init=False)

    def __post_init__(self):
        ports = self.ports()
        self.id2int = {k: i for i, k in enumerate(ports)}
        self.int2id = {v: k for k, v in self.id2int.items()}

        collector = ShortestPathCollector()
        # create endpoint for each device, each pod, each interface of each device
        collector.node(*self.int2id.keys())

        for device in self.topo.values():
            inames = device.inames()
            for iname in inames:
                collector.biedge(self.id2int[device.id], self.id2int[iname])

        for src, dsts in self.topo.cables.items():
            collector.biedge(self.id2int[src], *map(self.id2int.get, dsts))

        for pod, device in self.binds.items():
            collector.biedge(self.id2int[pod], self.id2int[device])

        podInts = {self.id2int[id] for id in self.pods}
        types = {k: {self.id2int[p.id] for p in v} for k, v in self.pods.types.items()}
        for pod, val in self.pods.items():
            pInt = self.id2int[pod]
            sameTypes = types.get(val.name)
            podresult = collector.shortestPaths(pInt, podInts, sameTypes)
            paths = {k: [LinkPath.aspath(self, tv) for tv in v] for k, v in podresult.items() if k in podInts}
            for k in podInts:
                if k not in paths:
                    paths[k] = []
            self.paths[pInt] = paths

    def weaks(self):
        return {self.int2id[i] for i in self.weakInts}

    def turn(self, port: str | Device | Pod | DeviceInterface, ison: bool):
        if isinstance(port, Device):
            id = port.id
        elif isinstance(port, Pod):
            id = port.id
        elif isinstance(port, tuple):
            sw, i = port
            id = sw.iname(i)
        else:
            id = port
        assert id in self.id2int
        id = self.id2int[id]
        if not ison:
            self.weakInts.add(id)
        elif id in self.weakInts:
            self.weakInts.remove(id)

    def off(self, *ports: str | Device | Pod | DeviceInterface):
        for port in ports:
            self.turn(port, False)

    def on(self, *ports: str | Device | Pod | DeviceInterface):
        for port in ports:
            self.turn(port, True)

    def state(self, source: str, target: str):
        # return a tuple of [healthy paths, weakpaths]
        assert source in self.pods and target in self.pods
        rawPaths = self.paths[self.id2int[source]][self.id2int[target]]
        healthyPaths: list[LinkPath] = []
        weakPaths: list[LinkPath] = []
        for path in rawPaths:
            if path.weak():
                weakPaths.append(path)
            else:
                healthyPaths.append(path)
        return healthyPaths, weakPaths


@dataclass
class LinkPath(Serializable, list[int]):
    network: FreezedNetwork = field(default_factory=FreezedNetwork)

    @classmethod
    def aspath(cls, network: FreezedNetwork, nodes: list[int]):
        result = LinkPath(network)
        result.extend(nodes)
        return result

    @cached_property
    def readable(self):
        return [self.network.int2id.get(v, "!unknown") for v in self]

    def weak(self):
        return any(x in self.network.weakInts for x in self)


if __name__ == "__main__":
    from .pod import PodConfig
    pods = PodContainer()
    pod0 = Pod("sm2", 0)
    pod1 = Pod("csdb", 0)
    pods.pod(pod0, pod1)

    host0 = Device("host-0")
    host1 = Device("host-1")
    sw0 = Device("tor-0")
    sw1 = Device("tor-1")
    topo = NetworkTopo()
    topo.device(host0, host1, sw0, sw1)
    topo.cable((host0, 0), (sw0, 0))
    topo.cable((host0, 1), (sw1, 0))
    topo.cable((host1, 0), (sw0, 1))
    topo.cable((host1, 1), (sw1, 1))

    net = Network(topo, pods)
    net.bind(pod0, host0)
    net.bind(pod1, host1)

    fnet = net.freeze()
    fnet.off((host0, 0))
    healthy, weak = fnet.state("sm2-0", "csdb-0")
    print("Healthy:")
    for path in healthy:
        print(path.readable)
    print("Weak:")
    for path in weak:
        print(path.readable)

    from ..generator import ProbabilityConnectionStateGenerator
    gen = ProbabilityConnectionStateGenerator()
    gen.fromNetwork(fnet)
    print("Probabilities:")
    print(gen.probabilities)
    gen.generate().display()
