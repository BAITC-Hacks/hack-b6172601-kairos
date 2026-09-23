"""Behavior checks for the findings refinement."""
import pandas as pd

from pipeline.roles import add_roles


def test_coordinator_two_pass_and_seed_exclusion():
    metrics = pd.DataFrame({
        "gid": [1, 2, 3, 4, 5], "is_seed": [True, False, False, False, False],
        "in_deg": [5, 5, 2, 3, 1], "out_deg": [2, 2, 0, 0, 0],
        "in_kzt": [100] * 5, "out_kzt": [100] * 5,
        "pass_through": [1.] * 5, "depth": [0, 1, 2, 2, 2],
        "truncated": [False] * 5, "cluster_id": [0, 1, 1, 1, 1],
        "betweenness": [0.] * 5, "seed_sources_2hop": [1] * 5,
        "fast_pass_share": [0.] * 5,
    })
    edges = pd.DataFrame({"src": [1, 2, 1, 2, 5, 1], "dst": [3, 3, 4, 4, 4, 5]})
    result = add_roles(metrics, edges).set_index("gid")
    assert result.loc[1, "role"] == "consolidator"
    assert result.loc[3, "role"] == "coordinator"
    assert result.loc[4, "role"] == "coordinator"
    assert result.loc[5, "role"] != "coordinator"


def test_findings_dates_boundaries_and_distinct_branches():
    import networkx as nx
    from pipeline.findings import add_findings, FINDING_TEXT, scatter_gather_targets

    graph = nx.DiGraph([(1, 2), (1, 3), (2, 4), (3, 5), (5, 4), (4, 1)])
    assert 4 in scatter_gather_targets(graph)
    assert not scatter_gather_targets(nx.DiGraph([(1, 2), (2, 3), (3, 1)]))
    metrics = pd.DataFrame({"gid": [4, 8], "seed_payers_direct": [2, 1],
                            "fast_pass_share": [.8, .9], "out_kzt": [100000, 99999]})
    tx = pd.DataFrame({"src": [1, 2, 3, 1], "dst": [4] * 4,
                       "date": pd.to_datetime(["2026-07-01 01:00", "2026-07-01 02:00",
                                              "2026-07-01 03:00", "2026-07-02 01:00"])})
    result = add_findings(metrics, tx, graph)
    assert all(result[flag].dtype == bool for flag in FINDING_TEXT)
    assert result.loc[0, list(FINDING_TEXT)].all()
    assert not result.loc[1, list(FINDING_TEXT)].any()
    assert "converge" in result.loc[0, "findings"]


def test_continuation_uses_visible_peers_and_exports_only_cutoffs():
    from pipeline.continuation import add_continuation, extension_requests
    metrics = pd.DataFrame({
        "gid": [1, 2, 3, 4, 5], "depth": [1, 2, 3, 4, 0],
        "in_deg": [1] * 5, "in_kzt": [100] * 5,
        "out_deg": [1, 1, 0, 0, 0], "truncated": [False, False, False, True, False],
        "taint_kzt": [100] * 5, "evidence": ["original"] * 5,
    })
    result = add_continuation(metrics)
    assert abs(result.loc[3, "p_continues"] - 2 / 3) < 1e-12
    assert result.loc[[0, 1, 2, 4], "p_continues"].isna().all()
    assert extension_requests(result).gid.tolist() == [4]
    assert "67%" in result.loc[3, "evidence"]
    assert add_continuation(metrics.iloc[[3]]).p_continues.isna().all()
