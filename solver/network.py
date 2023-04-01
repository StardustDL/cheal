from dataclasses import dataclass, field
from collections import defaultdict, deque
from itertools import combinations
import random
from .pod import Pod, PodManager
from .connection import ConnectionState


@dataclass
class ShortestPathCollector:
    nodes: set[int] = field(default_factory=set)
    edges: dict[int, set[int]] = field(default_factory=dict)

    def node(self, *ids: int):
        for item in ids:
            assert item not in self.nodes
            self.nodes.add(item)
            self.edges[item] = set()

    def edge(self, source: int, *targets: int):
        assert source in self.edges
        nexts = self.edges[source]
        for target in targets:
            assert target in self.nodes and target not in nexts
            nexts.add(target)

    def biedge(self, source: int, *targets: int):
        assert source in self.edges
        for target in targets:
            assert target in self.nodes
            self.edge(source, target)
            self.edge(target, source)

    def shortestPaths(self, source: int):
        assert source in self.nodes
        dist: dict[int, int] = {source: 0}
        queue = deque([source])
        while queue:
            u = queue.popleft()
            assert u in dist
            for v in self.edges[u]:
                if v not in dist:
                    dist[v] = dist[u] + 1
                    queue.append(v)

        result: dict[int, list[list[int]]] = defaultdict(list)
        result[source] = [[source]]

        sortedNodes = sorted(dist.keys(), key=dist.get)
        for u in sortedNodes:
            for v in self.edges[u]:
                if v in dist and dist[v] == dist[u] + 1:
                    for pathU in result[u]:
                        result[v].append(pathU + [v])
        return result


@dataclass
class Switch:
    id: str
    interfaces: int = field(default=2)

    def iname(self, num: int):
        assert 0 <= num < self.interfaces
        return f"{self.id}:{num}"

    def inames(self):
        return [self.iname(i) for i in range(self.interfaces)]


@dataclass
class Host(Switch):
    pods: set[str] = field(default_factory=set)


@dataclass
class Network:
    pods: PodManager = field(default_factory=PodManager)
    devices: dict[str, Switch] = field(default_factory=dict, init=False)
    interfaces: dict[str, Switch] = field(default_factory=dict, init=False)
    links: dict[str, set[str]] = field(default_factory=dict, init=False)

    def device(self, *devices: Switch):
        for device in devices:
            assert device.id not in self.devices
            self.devices[device.id] = device
            for iname in device.inames():
                assert iname not in self.interfaces
                self.interfaces[iname] = device
            if isinstance(device, Host):
                for pod in device.pods:
                    assert pod in self.pods
                    assert pod not in self.interfaces

    def link(self, source: tuple[Switch, int], target: tuple[Switch, int]):
        sW, sI = source
        tW, tI = target
        assert sW.id in self.devices and tW.id in self.devices
        assert sI < sW.interfaces and tI < tW.interfaces
        sI = sW.iname(sI)
        tI = tW.iname(tI)
        if sI > tI:
            sI, tI = tI, sI
        if sI not in self.links:
            self.links[sI] = set()
        self.links[sI].add(tI)


@dataclass
class NetworkState:
    network: Network
    id2int: dict[str, int] = field(default_factory=dict)
    int2id: dict[int, str] = field(default_factory=dict)
    paths: ShortestPathCollector = field(default_factory=ShortestPathCollector)
    computedPaths: dict[int, dict[int, list[list[int]]]
                        ] = field(default_factory=dict)
    weaks: set[str] = field(default_factory=set)

    def __post_init__(self):
        self.refresh(self.network)

    def refresh(self, network: Network):
        self.network = network
        self.buildGraph()
        self.computePaths()

    def buildGraph(self):
        interfaces = list(self.network.interfaces.keys()) + \
            list(self.network.pods.keys()) + list(self.network.devices.keys())
        id2int = {}
        for k in interfaces:
            id2int[k] = len(id2int)
        self.id2int = id2int
        self.int2id = {v: k for k, v in id2int.items()}

        self.paths = ShortestPathCollector()
        self.paths.node(*self.int2id.keys())

        # create endpoint for each device, each pod, each interface of each device

        for device in self.network.devices.values():
            inames = device.inames()
            for iname in inames:
                self.paths.biedge(id2int[device.id], id2int[iname])
            if isinstance(device, Host):
                for pod in device.pods:
                    self.paths.biedge(id2int[pod], id2int[device.id])

        for src, dsts in self.network.links.items():
            self.paths.biedge(id2int[src], *map(id2int.get, dsts))

    def computePaths(self):
        self.computedPaths.clear()
        podInts = {self.id2int[id] for id in self.network.pods}
        for pod in self.network.pods:
            pInt = self.id2int[pod]
            podresult = self.paths.shortestPaths(pInt)
            self.computedPaths[pInt] = {k: v for k,
                                        v in podresult.items() if k in podInts}

    def translateIntPath(self, raw: list[int]):
        return [self.int2id.get(v, "!unknown") for v in raw]

    def pathStates(self, source: str, target: str):
        # return a tuple of [healthy paths, weakpaths]
        assert source in self.network.pods and target in self.network.pods
        rawPaths = self.computedPaths[self.id2int[source]][self.id2int[target]]
        healthyPaths = []
        weakPaths = []
        weaks = [self.id2int[x] for x in self.weaks]
        for path in rawPaths:
            if any(x in path for x in weaks):
                weakPaths.append(path)
            else:
                healthyPaths.append(path)
        return healthyPaths, weakPaths

    def turn(self, endpoint: str | Switch | Pod | tuple[Switch, int], ison: bool):
        if isinstance(endpoint, Switch):
            id = endpoint.id
        elif isinstance(endpoint, Pod):
            id = endpoint.id
        elif isinstance(endpoint, tuple):
            sw, i = endpoint
            id = sw.iname(i)
        else:
            id = endpoint
        assert id in self.id2int
        if not ison:
            self.weaks.add(id)
        elif id in self.weaks:
            self.weaks.remove(id)

    def off(self, *endpoints: str | Switch | Pod | tuple[Switch, int]):
        for endpoint in endpoints:
            self.turn(endpoint, False)

    def on(self, *endpoints: str | Switch | Pod | tuple[Switch, int]):
        for endpoint in endpoints:
            self.turn(endpoint, True)


if __name__ == "__main__":
    pods = PodManager()
    pod0 = pods.single("sm2", 0)
    pod1 = pods.single("csdb", 0)
    host0 = Host("host-0", pods={pod0.id})
    host1 = Host("host-1", pods={pod1.id})
    sw0 = Switch("tor-0")
    sw1 = Switch("tor-1")
    net = Network(pods)
    net.device(host0, host1, sw0, sw1)
    net.link((host0, 0), (sw0, 0))
    net.link((host0, 1), (sw1, 0))
    net.link((host1, 0), (sw0, 1))
    net.link((host1, 1), (sw1, 1))
    state = NetworkState(net)
    state.off((host0, 0))
    healthy, weak = state.pathStates("sm2-0", "csdb-0")
    print("Healthy:")
    for path in healthy:
        print(state.translateIntPath(path))
    print("Weak:")
    for path in weak:
        print(state.translateIntPath(path))
    gen = ProbabilityConnectionStateGenerator(state)
    print(gen.probabilities)
    print(gen.generate().subhs)
