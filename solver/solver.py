from dataclasses import dataclass, field, replace
from functools import cached_property
from collections import defaultdict
import pyomo.environ as pyo
from .connection import ConnectionState
from .pod import Pod, PodManager
from abc import ABC, abstractmethod


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


@dataclass
class Solution:
    state: ConnectionState
    batches: list[Batch] = field(default_factory=list)

    @cached_property
    def coveredConnection(self):
        result = set()
        for batch in self.batches:
            result |= batch.coveredConnection
        return result

    @cached_property
    def majors(self):
        result = set()
        for batch in self.batches:
            result |= batch.majors
        return result


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
        solution = None

        k = 0
        while k <= len(state.pods):
            k += 1
            stateK = state.copy()
            for name, redu in stateK.pods.redus.items():
                stateK.pods.redundant(name, redu*k)
            solution = singleSolver.solve(stateK)
            assert len(solution.coveredConnection) <= totalWeak
            if len(solution.coveredConnection) == totalWeak:
                break
        else:
            assert False, "Failed to generate a valid solution."

        assert solution is not None, "Unexpected none solution."
        assert len(solution.batches) == 1
        return self.splitBatch(state, solution.batches[0])
