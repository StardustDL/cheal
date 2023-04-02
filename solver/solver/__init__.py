from dataclasses import dataclass, field, replace
from functools import cached_property
from collections import defaultdict
from ..model.connection import ConnectionState
from ..model.pod import Pod, PodContainer
from ..model.solution import Solution, Batch
from abc import ABC, abstractmethod
from rich import print
from math import ceil
from ..algorithms.cip import CIPSolver


class Solver(ABC):
    @abstractmethod
    def solve(self, state: ConnectionState) -> Solution:
        pass


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
            config = state.pods.configs[name]
            if config.redundancy is None:
                for pod in pods:
                    append(0, pod)
            else:
                assert config.redundancy >= 1, "The redundant is 0."
                i = 0
                cnt = 0
                for pod in pods:
                    if cnt < config.redundancy:
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
            for config in stateK.pods.configs.values():
                if config.redundancy != None:
                    config.redundancy *= k
            solution = singleSolver.solve(stateK)
            assert len(solution.coveredConnection) <= totalWeak
            return solution

        batchL, batchR = 1, 1
        type2pods = state.pods.types
        for name, config in state.pods.configs.items():
            assert config.redundancy is None or config.redundancy >= 0
            if config.redundancy == 0:
                continue
            totalPods = len(type2pods[name])
            batchR = max(batchR, ceil(totalPods / config.redundancy))
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
