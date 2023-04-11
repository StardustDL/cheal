from collections import defaultdict
from dataclasses import dataclass, field
from .connection import ConnectionState
from .pod import Pod
from functools import cached_property
from rich import print


@dataclass
class Batch:
    state: ConnectionState
    pods: list[Pod] = field(default_factory=list)

    @cached_property
    def coveredConnection(self):
        podSet = {p.id for p in self.pods}
        return {(source, target) for source, target in self.state.pairs if source in podSet or target in podSet}

    @cached_property
    def majors(self):
        majors = self.state.pods.majorTypes
        return {p.id for p in self.pods if p.name in majors}

    def __repr__(self) -> str:
        return f"{{{', '.join(pod.id for pod in self.pods)}}}"

    def display(self):
        majors = self.majors
        others = {p.id for p in self.pods} - majors
        pods = ", ".join(list(
            f"[bold]{name}[/bold]" for name in majors) + list(f"{name}" for name in others))
        print(f"""  Pods: {pods}
    include {len(self.pods)} pods ({len(self.majors)} majors), covered {len(self.coveredConnection)} connections""")

    def valid(self):
        name2pod = defaultdict(list)
        for pod in self.pods:
            name2pod[pod.name].append(pod)
        for name, pods in name2pod.items():
            config = self.state.pods.configs[name]
            if config.redundancy is not None and len(pods) > config.redundancy:
                return False
        return True


@dataclass
class Solution:
    state: ConnectionState
    batches: list[Batch] = field(default_factory=list)

    @cached_property
    def coveredConnection(self):
        result: set[tuple[str, str]] = set()
        for batch in self.batches:
            result |= batch.coveredConnection
        return result

    @cached_property
    def majors(self):
        result: set[str] = set()
        for batch in self.batches:
            result |= batch.majors
        return result

    @cached_property
    def pods(self):
        result: set[str] = set()
        for batch in self.batches:
            result |= {p.id for p in batch.pods}
        return result

    @cached_property
    def evaluated(self):
        return (len(self.coveredConnection), len(self.batches), len(self.majors), len(self.pods))

    def __repr__(self) -> str:
        return f"[{'; '.join(str(batch) for batch in self.batches)}] @ {self.evaluated}"

    def display(self):
        totalPairs = len(self.state.pairs)
        print(f"Solution:")
        print(f"""  {len(self.batches)} batches
  include {len(self.pods)} / {len(self.state.pods)} pods ({len(self.majors)} majors)
  covered {len(self.coveredConnection)} / {totalPairs} connections""")
        for i, batch in enumerate(self.batches):
            print(f"Batch {i+1} / {len(self.batches)}:")
            batch.display()

    def valid(self):
        return all(batch.valid() for batch in self.batches)
