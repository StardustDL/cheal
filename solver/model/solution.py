from collections import defaultdict
from dataclasses import dataclass, field
from .connection import ConnectionState
from .pod import Pod
from functools import cached_property
from rich import print
from ..serialization import Serializable
from . import ExecutionStatus


@dataclass
class Batch(Serializable, list[Pod]):

    def coveredConnection(self, state: ConnectionState):
        podSet = {p.id for p in self}
        return {(source, target) for source, target in state.pairs if source in podSet or target in podSet}

    def majors(self, state: ConnectionState):
        majors = state.pods.majorTypes
        return {p.id for p in self if p.name in majors}

    def __repr__(self) -> str:
        return f"{{{', '.join(pod.id for pod in self)}}}"

    def display(self, state: ConnectionState):
        majors = self.majors(state)
        others = {p.id for p in self} - majors
        pods = ", ".join(list(
            f"[bold]{name}[/bold]" for name in majors) + list(f"{name}" for name in others))
        print(f"""  Pods: {pods}
    include {len(self)} pods ({len(majors)} majors), covered {len(self.coveredConnection(state))} connections""")

    def valid(self, state: ConnectionState):
        name2pod = defaultdict(list)
        for pod in self:
            name2pod[pod.name].append(pod)
        for name, pods in name2pod.items():
            config = state.pods.configs[name]
            if config.redundancy is not None and len(pods) > config.redundancy:
                return False
        return True


@dataclass
class Solution(Serializable, list[Batch]):
    state: ConnectionState = field(default_factory=ConnectionState)
    status: ExecutionStatus = field(default_factory=ExecutionStatus)

    @cached_property
    def coveredConnection(self):
        result: set[tuple[str, str]] = set()
        for batch in self:
            result |= batch.coveredConnection(self.state)
        return result

    @cached_property
    def majors(self):
        result: set[str] = set()
        for batch in self:
            result |= batch.majors(self.state)
        return result

    @cached_property
    def pods(self):
        result: set[str] = set()
        for batch in self:
            result |= {p.id for p in batch}
        return result

    @cached_property
    def evaluated(self):
        return (len(self.coveredConnection), len(self), len(self.majors), len(self.pods))

    def __repr__(self) -> str:
        return f"[{'; '.join(str(batch) for batch in self)}] @ {self.evaluated}"

    def display(self):
        totalPairs = len(self.state.pairs)
        print(f"Solution:")
        print(f"""  {len(self)} batches
  include {len(self.pods)} / {len(self.state.pods)} pods ({len(self.majors)} majors)
  covered {len(self.coveredConnection)} / {totalPairs} connections""")
        for i, batch in enumerate(self):
            print(f"Batch {i+1} / {len(self)}:")
            batch.display(self.state)
        self.status.display()
        

    def valid(self):
        return all(batch.valid(self.state) for batch in self)
