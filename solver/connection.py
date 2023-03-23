from dataclasses import dataclass, field, replace
from .pod import PodManager, Pod


@dataclass
class ConnectionState:
    pods: PodManager
    subhs: dict[str, list[str]] = field(default_factory=dict)

    def copy(self):
        return ConnectionState(pods=self.pods.copy(),
                               subhs={k: v.copy() for k, v in self.subhs.items()})

    def pairs(self):
        return [(source, target) for source, targets in self.subhs.items() for target in targets]

    def weak(self, source: str | Pod, *targets: str | Pod):
        if isinstance(source, str):
            source = Pod(source)
        assert source.id in self.pods, f"Pod '{source.id}' not found"
        if source.id not in self.subhs:
            self.subhs[source.id] = []
        for target in targets:
            if isinstance(target, str):
                target = Pod(target)
            assert target.id in self.pods, f"Pod '{target.id}' not found"
            self.subhs[source.id].append(target.id)

    def weaks(self, *edges: tuple[str | Pod, str | Pod]):
        for x, y in edges:
            self.weak(x, y)
