import random
from .pod import PodManager
from .connection import ConnectionState


class NetworkGenerator:
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
