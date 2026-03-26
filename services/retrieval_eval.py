from typing import List


def mrr(relevant_ids: List, retrieved_ids: List) -> float:
    """Mean Reciprocal Rank for a single query."""
    for rank, rid in enumerate(retrieved_ids, start=1):
        if rid in relevant_ids:
            return 1.0 / rank
    return 0.0


def recall_at_k(relevant_ids: List, retrieved_ids: List, k: int) -> float:
    """Fraction of relevant items found in the top-k results."""
    if not relevant_ids:
        return 0.0
    hits = sum(1 for rid in retrieved_ids[:k] if rid in relevant_ids)
    return hits / len(relevant_ids)