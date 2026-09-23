"""Behavior checks for the findings refinement."""
import pandas as pd

from pipeline.config import CONFIG
from pipeline.roles import add_roles


def test_coordinator_two_pass_and_seed_exclusion():
    required = CONFIG.coordinator_min_consolidators
    candidate_gids = list(range(10, 10 + required))
    gids = [1, *candidate_gids, 100, 101, 102]
    metrics = pd.DataFrame({
        "gid": gids, "is_seed": [True] + [False] * required + [False, True, False],
        "in_deg": [5] + [5] * required + [required, required, 3],
        "out_deg": [required] * (required + 1) + [0, 0, 0],
        "in_kzt": [100_000] * len(gids), "out_kzt": [100_000] * len(gids),
        "pass_through": [1.] * len(gids), "depth": [0] + [1] * required + [2, 2, 2],
        "truncated": [False] * len(gids),
        "cluster_id": [0] + list(range(1, required + 1)) + [0, 0, 0],
        "betweenness": [0.] * len(gids), "seed_sources_2hop": [1] * len(gids),
        "fast_pass_share": [0.] * len(gids),
    })
    edges = pd.DataFrame({
        "src": [*candidate_gids, *candidate_gids, 1, 200, 201],
        "dst": [100] * required + [101] * required + [102] * 3,
    })
    # The source-cluster-only target has three payers from different communities.
    metrics = pd.concat([metrics, pd.DataFrame({
        "gid": [200, 201], "is_seed": [False, False], "in_deg": [1, 1],
        "out_deg": [1, 1], "in_kzt": [100_000] * 2, "out_kzt": [100_000] * 2,
        "pass_through": [1.] * 2, "depth": [1] * 2, "truncated": [False] * 2,
        "cluster_id": [20, 21], "betweenness": [0.] * 2,
        "seed_sources_2hop": [1] * 2, "fast_pass_share": [0.] * 2,
    })], ignore_index=True)
    result = add_roles(metrics, edges).set_index("gid")
    assert result.loc[1, "role"] == "consolidator"
    assert result.loc[100, "role"] == "coordinator"
    assert result.loc[100, "consolidator_payers"] == required
    assert result.loc[101, "role"] != "coordinator"  # A seed never takes this role.
    assert result.loc[102, "source_clusters"] >= 2
    assert result.loc[102, "consolidator_payers"] == 1
    assert result.loc[102, "role"] != "coordinator"


def test_findings_dates_boundaries_and_distinct_branches():
    import networkx as nx
    from pipeline.findings import add_findings, FINDING_TEXT, scatter_gather_targets

    floor = CONFIG.scatter_gather_min_edge_kzt
    graph = nx.DiGraph()
    graph.add_weighted_edges_from([
        (1, 2, floor), (2, 4, floor),
        (1, 3, floor), (3, 5, floor), (5, 4, floor),
        (1, 6, floor), (6, 4, floor), (4, 1, floor),
    ], weight="sum_kzt")
    assert 4 in scatter_gather_targets(graph)
    assert 1 not in scatter_gather_targets(graph)  # Closing cycle is not a branch.
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


def test_scatter_gather_requires_three_qualified_simple_paths_from_one_source():
    import networkx as nx
    from pipeline.findings import scatter_gather_targets

    floor = CONFIG.scatter_gather_min_edge_kzt

    def targets(edges):
        graph = nx.DiGraph()
        graph.add_weighted_edges_from(edges, weight="sum_kzt")
        return scatter_gather_targets(graph)

    branches = [(1, 2, floor), (2, 9, floor),
                (1, 3, floor), (3, 9, floor),
                (1, 4, floor), (4, 9, floor)]
    assert 9 in targets(branches)  # The exact amount boundary qualifies.
    assert 9 not in targets(branches[:4])
    for edge_index in (4, 5):
        with_low_edge = branches.copy()
        source, target, _ = with_low_edge[edge_index]
        with_low_edge[edge_index] = (source, target, floor - 1)
        assert 9 not in targets(with_low_edge)
    assert 9 not in targets(branches[:4] + [(2, 5, floor), (5, 9, floor)])
    assert 9 not in targets(branches[:4] + [(7, 4, floor), (4, 9, floor)])
    assert 9 not in targets(branches[:4] + [(1, 4, floor), (4, 5, floor - 1),
                                            (5, 9, floor)])
    assert 9 not in targets(branches[:4] + [(1, 4, floor), (4, 1, floor),
                                            (1, 9, floor)])
    assert 9 not in targets(branches[:4] + [(1, 4, floor), (4, 5, floor),
                                            (5, 6, floor), (6, 9, floor)])


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


def test_skeleton_intersection_small_edges_and_levels():
    import networkx as nx
    from pipeline.skeleton import add_skeleton
    edges = pd.DataFrame({"src": [1, 2, 1, 6], "dst": [2, 3, 4, 3],
                          "sum_kzt": [100, 100, .1, 100]})
    graph = nx.from_pandas_edgelist(edges, "src", "dst", create_using=nx.DiGraph)
    metrics = pd.DataFrame({
        "gid": [1, 2, 3, 4, 6], "is_seed": [True, False, False, False, False],
        "role": ["peripheral", "transit", "coordinator", "coordinator", "peripheral"],
        "taint_kzt": [0, 100, 100, 100, 0], "in_kzt": [0, 100, 200, 100, 0],
    })
    result, selected = add_skeleton(metrics, edges, graph)
    assert list(zip(selected.src, selected.dst)) == [(1, 2), (2, 3)]
    assert result.hierarchy_level.tolist() == [0, 1, 2, -1, -1]
    assert result.in_skeleton.dtype == bool
    metrics["role"] = "peripheral"
    assert add_skeleton(metrics, edges, graph)[1].empty


def test_payout_flag_all_conditions_and_exact_priority_discount():
    from pipeline.findings import add_payout_flag
    from pipeline.priority import add_priority
    metrics = pd.DataFrame({
        "gid": [1, 2, 3, 4], "out_deg": [10, 10, 9, 10],
        "taint_share": [.19, .2, .1, .1], "evidence": ["1 payer; " + "x" * 170] * 4,
        "role": ["distributor"] * 4, "taint_kzt": [100] * 4,
        "seed_sources_2hop": [1] * 4, "pagerank": [.1] * 4,
        "betweenness": [0.] * 4, "is_seed": [False] * 4, "truncated": [False] * 4,
    })
    tx = pd.DataFrame({
        "src": [gid for gid in range(1, 5) for _ in range(10)],
        "date": pd.to_datetime(["2026-07-01"] * 40),
        "sum_kzt": [100.] * 30 + [1.] * 9 + [1000.],
    })
    baseline = add_priority(metrics)
    flagged = add_payout_flag(metrics, tx)
    assert flagged.likely_legit_payouts.tolist() == [True, False, False, False]
    assert flagged.role.tolist() == metrics.role.tolist()
    ranked = add_priority(flagged)
    assert ranked.loc[0, "priority_score"] == baseline.loc[0, "priority_score"] * .5
    assert ranked.loc[1, "priority_score"] == baseline.loc[1, "priority_score"]
    assert len(flagged.loc[0, "evidence"]) <= 200
    assert flagged.loc[0, "evidence"].endswith("verify before escalating.")


def test_seed_hub_requires_seed_and_preserves_priority():
    from pipeline.findings import add_seed_hub_flag
    metrics = pd.DataFrame({
        "gid": [1, 2, 3, 4], "is_seed": [True, True, False, True],
        "in_deg": [5, 0, 10, 4], "out_deg": [0, 20, 30, 19],
        "evidence": ["5 observed transfers."] * 4,
        "priority_score": [.1, .2, .3, .4], "role": ["consolidator"] * 4,
    })
    result = add_seed_hub_flag(metrics)
    assert result.seed_hub.tolist() == [True, True, False, False]
    pd.testing.assert_series_equal(result.priority_score, metrics.priority_score)
    pd.testing.assert_series_equal(result.role, metrics.role)
    assert "above street level" in result.loc[0, "evidence"]
    assert result.loc[2, "evidence"] == metrics.loc[2, "evidence"]


def test_blocking_prefers_downstream_impact_and_is_monotone(monkeypatch):
    import numpy as np
    from dataclasses import replace
    from pipeline import blocking
    from pipeline.taint import add_taint

    metrics = pd.DataFrame({
        "gid": [1, 2, 3, 4], "is_seed": [True, False, False, False],
        "in_kzt": [0, 100, 50, 50], "out_kzt": [100, 100, 0, 0],
        "role": ["peripheral", "transit", "terminal", "terminal"],
        "priority_score": [0, .5, 1, 1],
    })
    edges = pd.DataFrame({"src": [1, 2, 2], "dst": [2, 3, 4], "sum_kzt": [100., 50., 50.]})
    simulation = blocking.TaintSimulation(metrics, edges)
    np.testing.assert_allclose(simulation.trace(np.ones(4, dtype=bool)), add_taint(metrics, edges).taint_kzt)
    plan, limited = blocking.blocking_plan(metrics, edges)
    assert not limited
    assert plan.gid.tolist() == [2, 3, 4]
    assert plan.cut_share_cumulative.is_monotonic_increasing
    assert plan.cut_share_cumulative.iloc[0] == 1
    monkeypatch.setattr(blocking, "CONFIG", replace(blocking.CONFIG, blocking_max_seconds=0))
    fallback, limited = blocking.blocking_plan(metrics, edges)
    assert limited
    pd.testing.assert_frame_equal(fallback, plan)
    edges["sum_kzt"] = 0.
    assert blocking.blocking_plan(metrics, edges)[0].cut_share_cumulative.eq(0).all()


def test_blocking_preserves_original_dilution_and_bounds_cycles():
    import numpy as np
    from pipeline.blocking import TaintSimulation, blocking_plan
    metrics = pd.DataFrame({
        "gid": [1, 2, 3, 4], "is_seed": [True, False, False, False],
        "in_kzt": [0, 150, 100, 100], "out_kzt": [100, 200, 50, 0],
        "role": ["peripheral"] * 4, "priority_score": [0, 1, .8, .7],
    })
    edges = pd.DataFrame({"src": [1, 2, 3, 2], "dst": [2, 3, 2, 4],
                          "sum_kzt": [100., 100., 50., 100.]})
    model = TaintSimulation(metrics, edges)
    original = model.trace(np.ones(4, dtype=bool))
    after = model.trace(np.array([True, True, False, True]))
    assert (after <= original + 1e-9).all()
    assert after[3] == 50.  # Removing the other branch must not increase this share.
    plan, _ = blocking_plan(metrics, edges)
    assert plan.cut_share_cumulative.between(0, 1).all()
    assert plan.cut_share_cumulative.is_monotonic_increasing
