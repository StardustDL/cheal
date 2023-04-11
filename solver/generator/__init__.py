import random
from ..model.pod import PodContainer, Pod, PodConfig
from ..model.connection import ConnectionState
from ..model.network import FreezedNetwork
from ..serialization import Serializable
from itertools import combinations
from dataclasses import dataclass, field


class RandomConnectionStateGenerator:
    def pods(self, pods: PodContainer, podCount: int, typeCount: int, majorRate: float = 0.2):
        for i in range(podCount):
            pods.pod(Pod(f"type{random.randint(0, typeCount-1)}", i))
        for type, tpods in pods.types.items():
            config = PodConfig()
            if random.random() < majorRate:
                config.major = True
            config.redundancy = random.randint(0, max(0, len(tpods)))
            pods.configs[type] = config

    def state(self, state: ConnectionState, weaks: int):
        type2pods = state.pods.types
        types = list(type2pods.keys())
        assert len(types) > 1, "Must have more than 1 pod type."
        for _ in range(weaks):
            t1, t2 = map(type2pods.get, random.choices(types, k=2))
            assert t1 and t2, "The type must have pods."
            p1, p2 = random.choice(t1), random.choice(t2)
            state.weak(p1, p2)


@dataclass
class ProbabilityConnectionStateGenerator(Serializable):
    pods: PodContainer = field(default_factory=PodContainer)
    probabilities: dict[tuple[str, str], float] = field(default_factory=dict)

    @classmethod
    def fromNetwork(cls, network: FreezedNetwork):
        result = cls(network.pods.copy())
        for s, t in combinations(network.binds.keys(), 2):
            healthy, weak = network.state(s, t)
            total = (len(healthy) + len(weak))
            result.probabilities[(s, t)] = (len(weak) / total) if total > 0 else 0.0
        return result

    def generate(self):
        result = ConnectionState(self.pods)
        for (s, t), p in self.probabilities.items():
            if random.random() < p:
                result.weak(s, t)
            if random.random() < p:
                result.weak(t, s)
        return result
