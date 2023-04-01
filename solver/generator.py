import random
from .pod import PodManager
from .connection import ConnectionState
from .network import NetworkState
from itertools import combinations
from dataclasses import dataclass, field


class RandomConnectionStateGenerator:
    def pods(self, pods: PodManager, podCount: int, typeCount: int, majorRate: float = 0.2):
        for i in range(podCount):
            pods.single(f"type{random.randint(0, typeCount-1)}", i)
        for type in pods.types:
            if random.random() < majorRate:
                pods.major(type)
            pods.redundant(type, random.randint(
                0, max(0, len(pods.types)-1)))

    def state(self, state: ConnectionState, weaks: int):
        types = list(state.pods.types.keys())
        assert len(types) > 1, "Must have more than 1 pod type."
        for _ in range(weaks):
            t1, t2 = map(state.pods.types.get, random.choices(types, k=2))
            assert t1 and t2, "The type must have pods."
            p1, p2 = random.choice(t1), random.choice(t2)
            state.weak(p1, p2)


@dataclass
class ProbabilityConnectionStateGenerator:
    state: NetworkState
    probabilities: dict[tuple[str, str], float] = field(default_factory=dict)

    def __post_init__(self):
        pods = self.state.network.pods
        self.probabilities.clear()
        for s, t in combinations(pods.keys(), 2):
            healthy, weak = self.state.pathStates(s, t)
            self.probabilities[(s, t)] = len(weak) / (len(healthy) + len(weak))

    def generate(self):
        result = ConnectionState(self.state.network.pods)
        for (s, t), p in self.probabilities.items():
            if random.random() < p:
                result.weak(s, t)
            if random.random() < p:
                result.weak(t, s)
        return result
