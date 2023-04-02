from dataclasses import dataclass, field, replace
from .pod import PodContainer, Pod
from ..serialization import Serializable
from rich import print


@dataclass
class ConnectionState(Serializable, dict[str, list[str]]):
    pods: PodContainer = field(default_factory=PodContainer)

    def pairs(self):
        return [(source, target) for source, targets in self.items() for target in targets]

    def weak(self, source: str | Pod, *targets: str | Pod):
        if isinstance(source, str):
            source = Pod.fromId(source)
        assert source.id in self.pods, f"Pod '{source.id}' not found"
        if source.id not in self:
            self[source.id] = []
        for target in targets:
            if isinstance(target, str):
                target = Pod.fromId(target)
            assert target.id in self.pods, f"Pod '{target.id}' not found"
            self[source.id].append(target.id)

    def weaks(self, *edges: tuple[str | Pod, str | Pod]):
        for x, y in edges:
            self.weak(x, y)

    def display(self):
        self.pods.display()
        print(f"Weak Connections ({len(self.pairs())}): ")
        for source, targets in self.items():
            print(f"  {source} ({len(targets)}): {', '.join(targets)}")
