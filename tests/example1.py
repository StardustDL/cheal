from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from solver.model.connection import ConnectionState
    from solver.model.network import Network, NetworkTopo, FreezedNetwork
    from solver.model.pod import Pod, PodConfig, PodContainer
    from solver.model.solution import Solution, Batch
    from solver.generator import RandomConnectionStateGenerator, ProbabilityConnectionStateGenerator

    def submit(state: ConnectionState): pass

pods = PodContainer()

pods.pod(*[Pod("sm2", i) for i in range(4)])
pods.configs["sm2"] = PodConfig(3)
pods.pod(*[Pod("nsim", i) for i in range(3)])
pods.configs["nsim"] = PodConfig(1, True)
pods.pod(*[Pod("sbim", i) for i in range(3)])
pods.configs["sbim"] = PodConfig(1, True)
pods.pod(*[Pod("csdb", i) for i in range(2)])
pods.configs["csdb"] = PodConfig(1)
pods.pod(*[Pod("cslb", i) for i in range(2)])
pods.configs["cslb"] = PodConfig(1)
pods.connect("sm2", "csdb", "sbim", "nsim")
pods.connect("cslb", "sbim", "nsim")

state = ConnectionState(pods)

state.weaks(
    ("sm2-0", "sbim-2"),
    ("sm2-0", "csdb-0"),
    ("nsim-1", "sm2-0"),
    ("csdb-1", "sm2-0"),
    ("cslb-0", "nsim-0"),
    ("cslb-1", "sbim-0"),
    ("sbim-0", "cslb-1"),
    ("sm2-3", "sbim-0"),
    ("sm2-3", "nsim-0")
)

submit(state)