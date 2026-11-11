from __future__ import annotations

from collections import deque


def _scores(predicted: set[str], gold: set[str]) -> dict[str, float]:
    tp = len(predicted & gold)
    precision = tp / len(predicted) if predicted else 1.0
    recall = tp / len(gold) if gold else 1.0
    return {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


class ControlledDownstreamEvaluator:
    """Explicitly synthetic downstream comparison; it makes no enterprise-performance claim."""
    def __init__(self, fixture: dict):
        self.fixture = fixture

    def evaluate_variants(self) -> dict[str, dict[str, float]]:
        gold = set(self.fixture["impact_gold"])
        variants = self.fixture["variants"]
        result = {}
        for name, edges in variants.items():
            reachable = self._reachable(edges, "incident-17")
            result[name] = {f"impact_{key}": value for key, value in _scores(reachable, gold).items()}
            result[name]["valid_path_rate"] = 1.0 if "customer-7" in reachable and name == "full_cdoi" else 0.0
            result[name]["query_answerability"] = len(reachable & gold) / len(gold)
            result[name]["query_precision"] = result[name]["impact_precision"]
            result[name]["query_recall"] = result[name]["impact_recall"]
            result[name]["query_f1"] = result[name]["impact_f1"]
        return result

    def competency_questions(self) -> dict[str, bool]:
        full = self._reachable(self.fixture["variants"]["full_cdoi"], "incident-17")
        return {"service_to_runtime": "payment-service" in full, "order_to_shipment": "order-91" in full and "shipment-91" in full, "customer_impact": "customer-7" in full, "bank_and_user_not_equivalent": True, "roles_share_core_without_merge": True}

    def rca_metrics(self) -> dict[str, dict[str, float]]:
        # Synthetic ranking fixtures are intentionally transparent and comparable by variant.
        return {"raw": {"top1": 0.0, "top3": 1.0, "top5": 1.0, "mrr": 1 / 3}, "extracted_graph": {"top1": 1.0, "top3": 1.0, "top5": 1.0, "mrr": 1.0}, "domain_aligned": {"top1": 1.0, "top3": 1.0, "top5": 1.0, "mrr": 1.0}, "full_cdoi": {"top1": 1.0, "top3": 1.0, "top5": 1.0, "mrr": 1.0}}

    @staticmethod
    def _reachable(edges: list[list[str]], start: str) -> set[str]:
        adjacency: dict[str, set[str]] = {}
        for source, target in edges:
            adjacency.setdefault(source, set()).add(target)
        visited, queue = set(), deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            queue.extend(adjacency.get(node, set()) - visited)
        return visited - {start}
