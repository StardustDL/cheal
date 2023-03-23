from dataclasses import dataclass, field, replace
from typing import Iterable


@dataclass
class Pod:
    name: str
    no: int

    def __init__(self, name: str, no: int | None = None) -> None:
        if no is None:
            name, no = name.split('-')
            no = int(no)
        self.name = name
        self.no = no

    @property
    def id(self):
        return f"{self.name}-{self.no}"


@dataclass
class PodManager(dict[str, Pod]):
    types: dict[str, list[Pod]] = field(default_factory=dict)
    redus: dict[str, int] = field(default_factory=dict)
    majors: dict[str, bool] = field(default_factory=dict)

    def copy(self):
        return PodManager(types={k: v.copy() for k, v in self.types.items()},
                          redus={k: v for k, v in self.redus.items()},
                          majors={k: v for k, v in self.majors.items()})

    def allmajors(self):
        return {name for name, ismajor in self.majors.items() if ismajor}

    def single(self, name: str, no: int | None = None):
        pod = Pod(name, no)
        assert pod.id not in self
        if pod.name not in self.types:
            self.types[pod.name] = []
            self.redus[pod.name] = 0
            self.majors[pod.name] = False
        self.types[pod.name].append(pod)
        self[pod.id] = pod
        return pod

    def redundant(self, name: str, value: int):
        assert value >= 0
        assert name in self.redus
        self.redus[name] = value

    def major(self, name: str, value: bool = True):
        assert value >= 0
        assert name in self.majors
        self.majors[name] = value

    def multiple(self, name: str, nos: Iterable[int], redundant: int = 0, major: bool = False):
        result = [self.single(name, no) for no in nos]
        self.redundant(name, redundant)
        self.major(name, major)
        return result
