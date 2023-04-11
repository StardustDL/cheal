from dataclasses import dataclass, field
import pyomo.environ as pyo
from ..model.pod import Pod
from ..model.connection import ConnectionState


@dataclass
class CIPSolver:
    state: ConnectionState
    id2int: dict[str, int] = field(default_factory=dict, init=False)
    int2id: dict[int, str] = field(default_factory=dict, init=False)
    PR: list[tuple[list[int], int]] = field(default_factory=list, init=False)
    M: list[int] = field(default_factory=list, init=False)
    E: list[tuple[int, int]] = field(default_factory=list, init=False)
    model: pyo.ConcreteModel | None = field(default=None, init=False)

    def __post_init__(self):
        self.pods = self.state.pods
        id2int = {}
        for k in self.state.pods:
            id2int[k] = len(id2int)
        PR = [([id2int[p.id] for p in self.state.pods.types[k]], self.state.pods.configs[k].redundancy)
              for k in self.state.pods.types]
        M = sum([[id2int[p.id] for p in self.state.pods.types[k]]
                for k, c in self.state.pods.configs.items() if c.major], start=[])
        E = list(set((id2int[x], id2int[y])
                 for x, l in self.state.items() for y in l))
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

        selectInts = [i for i in range(len(self.id2int)) if abs(pyo.value(self.model.x[i]) - 1.0) < 0.1]
        selectPods = [self.pods[self.int2id[i]] for i in selectInts]

        return selectPods