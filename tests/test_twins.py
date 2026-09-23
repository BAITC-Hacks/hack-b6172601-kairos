"""Shared-source thresholds, transitive grouping and exact identifier contracts."""

import json

import networkx as nx
import pandas as pd

from app.api.viewer import csv_rows
from pipeline.twins import GROUP_COLUMNS, TWIN_HYPOTHESIS, add_shared_sources, twin_groups


def fixture(payer_sets):
    graph = nx.DiGraph()
    for gid, payers in payer_sets.items():
        graph.add_node(gid)
        graph.add_edges_from((payer, gid) for payer in payers)
    metrics = pd.DataFrame({"gid": list(payer_sets), "in_kzt": [100] * len(payer_sets)})
    return metrics, graph


def test_both_thresholds_are_inclusive_and_distinct_payers_are_required():
    metrics, graph = fixture({10: {1, 2, 3}, 11: {1, 2, 3, 4, 5, 6},
                              12: {1, 2}, 13: {1, 2, 3, 4, 5, 6, 7}, 14: set()})
    result = add_shared_sources(metrics, graph).set_index("gid")
    assert "11" in result.loc[10, "twin_gids"]  # 3 shared, Jaccard exactly .5.
    assert "13" not in result.loc[10, "twin_gids"]  # 3 shared, insufficient Jaccard.
    assert not result.loc[12, "shared_sources_twin"]  # Jaccard alone is insufficient.
    assert not result.loc[14, "shared_sources_twin"]
    assert result.loc[10, "twin_shared_payers"]["11"] == 3
    assert result.loc[11, "twin_shared_payers"]["10"] == 3


def test_transitive_group_does_not_invent_direct_pair_matches():
    metrics, graph = fixture({10: {1, 2, 3, 4}, 11: {2, 3, 4, 5}, 12: {3, 4, 5, 6}})
    result = add_shared_sources(metrics, graph)
    assert result.twin_group.nunique() == 1
    by_gid = result.set_index("gid")
    assert by_gid.loc[10, "twin_gids"] == ["11"]
    assert by_gid.loc[11, "twin_gids"] == ["10", "12"]
    groups = twin_groups(result, graph)
    assert list(groups.columns) == GROUP_COLUMNS
    assert json.loads(groups.iloc[0].gids) == ["10", "11", "12"]
    assert json.loads(groups.iloc[0].shared_payers) == ["2", "3", "4", "5"]
    assert groups.iloc[0].total_in_kzt == 300
    assert groups.iloc[0].hypothesis == TWIN_HYPOTHESIS
    reversed_result = add_shared_sources(metrics.iloc[::-1], nx.DiGraph(reversed(list(graph.edges))))
    assert dict(zip(result.gid, result.twin_group)) == dict(zip(reversed_result.gid, reversed_result.twin_group))


def test_twins_json_round_trip_preserves_large_identifiers_and_empty_export():
    large = 100000003115284100
    metrics, graph = fixture({large: {1, 2, 3}, large + 1: {1, 2, 3}})
    result = add_shared_sources(metrics, graph)
    for column in ("twin_gids", "twin_shared_payers"):
        result[column] = result[column].map(json.dumps)
    parsed = csv_rows(result.to_csv(index=False).encode())
    assert parsed[0]["gid"] == str(large)
    assert parsed[0]["twin_gids"] == [str(large + 1)]
    assert parsed[0]["twin_shared_payers"][str(large + 1)] == 3
    empty_metrics, empty_graph = fixture({10: set()})
    empty = twin_groups(add_shared_sources(empty_metrics, empty_graph), empty_graph)
    assert empty.empty and list(empty.columns) == GROUP_COLUMNS


def test_twin_finding_receives_the_configured_priority_bonus():
    from pipeline.config import CONFIG
    from pipeline.priority import add_priority
    metrics = pd.DataFrame({
        "taint_kzt": [100, 100], "seed_sources_2hop": [1, 1],
        "pagerank": [.1, .1], "betweenness": [.1, .1],
        "role": ["consolidator"] * 2, "is_seed": [False] * 2,
        "truncated": [False] * 2, "evidence": ["Observed flows"] * 2,
        "findings": ["", "Shared sources"], "shared_sources_twin": [False, True],
    })
    result = add_priority(metrics)
    assert result.priority_explanation.iloc[0]["finding_bonus"] == 0
    assert result.priority_explanation.iloc[1]["finding_bonus"] == CONFIG.finding_priority_bonus
    assert result.priority_score.iloc[1] > result.priority_score.iloc[0]
