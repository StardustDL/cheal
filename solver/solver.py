from dataclasses import dataclass, field, replace
from functools import cached_property
from collections import defaultdict
import pyomo.environ as pyo
from .connection import ConnectionState
from .pod import Pod, PodManager
from abc import ABC, abstractmethod
from rich import print
from math import ceil


@dataclass
class Batch:
    state: ConnectionState
    pods: list[Pod] = field(default_factory=list)

    @cached_property
    def coveredConnection(self):
        podSet = {p.id for p in self.pods}
        return {(source, target) for source, target in self.state.pairs() if source in podSet or target in podSet}

    @cached_property
    def majors(self):
        majors = self.state.pods.allmajors()
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
            redu = self.state.pods.redus.get(name, None)
            if redu is None:
                continue
            if len(pods) > redu:
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
        totalPairs = len(self.state.pairs())
        print(f"Solution:")
        print(f"""  {len(self.batches)} batches
  include {len(self.pods)} / {len(self.state.pods)} pods ({len(self.majors)} majors)
  covered {len(self.coveredConnection)} / {totalPairs} connections""")
        for i, batch in enumerate(self.batches):
            print(f"Batch {i+1} / {len(self.batches)}:")
            batch.display()

    def valid(self):
        return all(batch.valid() for batch in self.batches)


class Solver(ABC):
    @abstractmethod
    def solve(self, state: ConnectionState) -> Solution:
        pass


@dataclass
class CIPSolver:
    state: ConnectionState
    id2int: dict[str, int] = field(default_factory=dict)
    int2id: dict[int, str] = field(default_factory=dict)
    PR: list[tuple[list[int], int]] = field(default_factory=list)
    M: list[int] = field(default_factory=list)
    E: list[tuple[int, int]] = field(default_factory=list)
    model: pyo.ConcreteModel | None = None

    def __post_init__(self):
        self.pods = self.state.pods
        id2int = {}
        for k in self.state.pods:
            id2int[k] = len(id2int)
        PR = [([id2int[p.id] for p in self.state.pods.types[k]], self.state.pods.redus[k])
              for k in self.state.pods.types]
        M = sum([[id2int[p.id] for p in self.state.pods.types[k]]
                for k, m in self.state.pods.majors.items() if m], start=[])
        E = list(set((id2int[x], id2int[y])
                 for x, l in self.state.subhs.items() for y in l))
        self.id2int = id2int
        self.int2id = {v: k for k, v in id2int.items()}
        self.PR = PR
        self.M = M
        self.E = E

    def compile(self, C1=100.0, C3=10.0, C4=1.0):
        n = sum(len(l) for l, _ in self.PR)

        model = pyo.ConcreteModel()

        # model.x = pyo.Var([1,2], domain=pyo.NonNegativeReals)
        # model.OBJ = pyo.Objective(expr = 2*model.x[1] + 3*model.x[2])
        # model.Constraint1 = pyo.Constraint(expr = 3*model.x[1] + 4*model.x[2] >= 1)

        model.x = pyo.Var(list(range(n)), domain=pyo.Binary)
        model.OBJ = pyo.Objective(expr=C1 * sum((1 - (1 - model.x[i]) * (1 - model.x[j])) for i, j in self.E)
                                  - C3 * sum(model.x[i] for i in self.M)
                                  - C4 * sum(model.x[i] for i in range(n)), sense=pyo.maximize)
        model.cons = pyo.ConstraintList()
        for l, r in self.PR:
            s = 0
            for i in l:
                s = s + model.x[i]
            model.cons.add(s <= r)
        self.model = model
        return self

    def solve(self) -> list[Pod]:
        assert self.model is not None

        opt = pyo.SolverFactory('scip')
        opt.solve(self.model)

        selectInts = [i for i in range(len(self.id2int)) if int(
            pyo.value(self.model.x[i])) == 1]
        selectPods = [self.pods[self.int2id[i]] for i in selectInts]

        return selectPods


@dataclass
class CIPSingleBatchSolver(Solver):
    C1: float = 1000.0
    C3: float = 10.0
    C4: float = 1.0

    def solve(self, state: ConnectionState) -> Solution:
        pods = CIPSolver(state).compile(self.C1, self.C3, self.C4).solve()
        return Solution(state=state, batches=[Batch(state=state, pods=pods)])


@dataclass
class CIPMultipleBatchSolver(Solver):
    C1: float = 1000.0
    C2: float = 100.0
    C3: float = 10.0
    C4: float = 1.0

    def splitBatch(self, state: ConnectionState, batch: Batch):
        batches: list[Batch] = []
        name2pods: dict[str, list[Pod]] = defaultdict(list)
        for pod in batch.pods:
            name2pods[pod.name].append(pod)

        def append(i: int, pod: Pod):
            while i >= len(batches):
                batches.append(Batch(state=state, pods=[]))
            batches[i].pods.append(pod)

        for name, pods in name2pods.items():
            redu = state.pods.redus.get(name, None)
            if redu is None:
                for pod in pods:
                    append(0, pod)
            else:
                assert redu >= 1, "The redundant is 0."
                i = 0
                cnt = 0
                for pod in pods:
                    if cnt < redu:
                        append(i, pod)
                        cnt += 1
                    else:
                        i += 1
                        cnt = 1
                        append(i, pod)

        return batches

    def solve(self, state: ConnectionState) -> Solution:
        totalWeak = len(state.pairs())
        singleSolver = CIPSingleBatchSolver(self.C1, self.C3, self.C4)

        def solveKBatch(k: int):
            stateK = state.copy()
            for name, redu in list(stateK.pods.redus.items()):
                stateK.pods.redundant(name, redu*k)
            solution = singleSolver.solve(stateK)
            assert len(solution.coveredConnection) <= totalWeak
            return solution

        batchL, batchR = 1, 1
        for name, redu in state.pods.redus.items():
            assert redu >= 0
            if redu == 0:
                continue
            totalPods = len(state.pods.types[name])
            batchR = max(batchR, ceil(totalPods / redu))
        batchCount = batchR
        targetSolution = solveKBatch(batchCount)
        maxCovered = len(targetSolution.coveredConnection)

        while batchL <= batchR:
            mid = (batchL + batchR) // 2
            solution = solveKBatch(mid)
            if len(solution.coveredConnection) < maxCovered:
                batchL = mid+1
            else:
                assert len(solution.coveredConnection) == maxCovered
                assert mid <= batchCount
                batchCount = mid
                targetSolution = solution
                batchR = mid-1

        assert len(targetSolution.batches) == 1 and len(
            targetSolution.coveredConnection) == maxCovered, "Unexpected none solution."

        finalSolution = Solution(
            state=state, batches=self.splitBatch(state, targetSolution.batches[0]))
        assert len(finalSolution.batches) == batchCount, \
            f"The batch count is not equal, {batchCount=}, {len(finalSolution.batches)=}."
        
        assert finalSolution.valid()

        return finalSolution
