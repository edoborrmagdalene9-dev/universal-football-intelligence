"""Portfolio overlap and Hamming-distance validation."""
from __future__ import annotations
from collections.abc import Iterable, Sequence


def hamming_distance(lineup_a: Iterable[str], lineup_b: Iterable[str]) -> int:
    return len(set(lineup_a).symmetric_difference(set(lineup_b)))


def overlap_count(lineup_a: Iterable[str], lineup_b: Iterable[str]) -> int:
    return len(set(lineup_a).intersection(set(lineup_b)))


def validate_portfolio(lineups: Sequence[Iterable[str]], min_hamming_distance: int) -> None:
    if min_hamming_distance < 0:
        raise ValueError("minimum distance cannot be negative")
    normalized = [set(x) for x in lineups]
    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            d = hamming_distance(normalized[i], normalized[j])
            if d < min_hamming_distance:
                raise ValueError(f"lineups {i} and {j} too similar: {d} < {min_hamming_distance}")
