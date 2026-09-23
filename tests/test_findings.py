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
