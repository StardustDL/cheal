from collections import defaultdict
from dataclasses import dataclass, field, replace, asdict
from typing import Iterable
from rich import print
from ..serialization import Serializable


@dataclass
class Pod(Serializable):
    name: str = "pod"
    no: int = 0

    @property
    def id(self):
        return f"{self.name}-{self.no}"

    @classmethod
    def fromId(self, id: str):
        assert "-" in id
        name, id = id.split("-", maxsplit=1)
        return Pod(name, int(id))

    @classmethod
    def fromRange(self, name: str, nos: Iterable[int]):
        return [Pod(name, i) for i in nos]


@dataclass
class PodConfig(Serializable):
    redundancy: int | None = None
    major: bool = False


@dataclass
class PodContainer(Serializable, dict[str, Pod]):
    configs: dict[str, PodConfig] = field(default_factory=lambda: defaultdict(PodConfig))

    def __post_init__(self):
        configs = defaultdict(PodConfig)
        for k, v in self.configs.items():
            configs[k] = v
        self.configs = configs

    def pod(self, *pods: Pod):
        for pod in pods:
            assert pod.id not in self
            self[pod.id] = pod

    @property
    def types(self):
        types: dict[str, list[Pod]] = defaultdict(list)
        for pod in self.values():
            types[pod.name].append(pod)
        return types

    @property
    def majorTypes(self):
        return {k for k, v in self.configs.items() if v.major}

    def display(self):
        types = self.types
        print(f"{len(self)} Pods (in {len(types)} types):")
        for name, pods in types.items():
            config = self.configs[name]
            nameStr = f"[bold]{name}[/bold]" if config.major else f"{name}"
            reduStr = f"<={config.redundancy}" if config.redundancy is not None else "N/A"
            print(
                f"  {nameStr} ({len(pods)}, {reduStr}): {', '.join(pod.id for pod in pods)}")