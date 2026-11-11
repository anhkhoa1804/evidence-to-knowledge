from __future__ import annotations

from typing import Protocol

from rdflib import Graph, RDFS, URIRef


class Reasoner(Protocol):
    name: str
    def has_taxonomy_cycle(self, graph: Graph, subject: URIRef, parent: URIRef) -> bool: ...


class TaxonomyReasoner:
    name = "rdflib-taxonomy"

    def has_taxonomy_cycle(self, graph: Graph, subject: URIRef, parent: URIRef) -> bool:
        frontier = [parent]
        seen: set[URIRef] = set()
        while frontier:
            node = frontier.pop()
            if node in seen:
                continue
            seen.add(node)
            if node == subject:
                return True
            frontier.extend(graph.objects(node, RDFS.subClassOf))
        return False
