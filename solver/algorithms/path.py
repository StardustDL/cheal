from dataclasses import dataclass, field
from collections import defaultdict, deque


@dataclass
class ShortestPathCollector:
    nodes: set[int] = field(default_factory=set)
    edges: dict[int, set[int]] = field(default_factory=dict)

    def node(self, *ids: int):
        for item in ids:
            assert item not in self.nodes
            self.nodes.add(item)
            self.edges[item] = set()

    def edge(self, source: int, *targets: int):
        assert source in self.edges
        nexts = self.edges[source]
        for target in targets:
            assert target in self.nodes and target not in nexts
            nexts.add(target)

    def biedge(self, source: int, *targets: int):
        assert source in self.edges
        for target in targets:
            assert target in self.nodes
            self.edge(source, target)
            self.edge(target, source)

    def shortestPaths(self, source: int, endpoints: set[int] | None = None, ignored: set[int] | None = None):
        ignored = ignored or set()
        endpoints = endpoints or set()
        assert source in self.nodes
        dist: dict[int, int] = {source: 0}
        queue = deque([source])
        while queue:
            u = queue.popleft()
            assert u in dist
            if u != source and u in endpoints:
                continue
            for v in self.edges[u]:
                if v in ignored:
                    continue
                if v not in dist:
                    dist[v] = dist[u] + 1
                    queue.append(v)

        result: dict[int, list[list[int]]] = defaultdict(list)
        result[source] = [[source]]

        sortedNodes = sorted(dist.keys(), key=dist.get)
        for u in sortedNodes:
            if u != source and u in endpoints:
                continue
            for v in self.edges[u]:
                if v in ignored:
                    continue
                if v in dist and dist[v] == dist[u] + 1:
                    for pathU in result[u]:
                        result[v].append(pathU + [v])
        return result
