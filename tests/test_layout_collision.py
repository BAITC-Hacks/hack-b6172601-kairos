"""Geometry contracts for exported positions, including coincident nodes."""
import math
from pipeline.layout import remove_overlaps


def test_exported_circles_never_overlap_and_are_deterministic():
    positions = {i: (i % 5, i % 7) for i in range(100)}
    priorities = {i: (i % 11) / 10 for i in positions}
    result = remove_overlaps(positions, priorities)
    assert result == remove_overlaps(positions, priorities)
    assert set(result) == set(positions)
    for i, a in result.items():
        for j, b in result.items():
            if i < j:
                assert math.dist(a, b) >= 8 + 9 * (priorities[i] + priorities[j]) - 1e-8


def test_empty_and_already_separated_layouts():
    assert remove_overlaps({}, {}) == {}
    points = {1: (0, 0), 2: (100, 100)}
    assert remove_overlaps(points, {1: 1, 2: 1}) == points
