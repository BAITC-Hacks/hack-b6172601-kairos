"""Role and priority explanations reflect the computations that produced them."""

import math

import pandas as pd

from pipeline.config import CONFIG, method_description
from pipeline.priority import add_priority
from pipeline.roles import add_roles


def test_role_trace_selects_first_match_and_reports_failed_thresholds():
    gids = [10, 11, 12, 20, 21, 22, 23]
    metrics = pd.DataFrame({
        "gid": gids,
        "is_seed": [False, False, False, False, True, False, False],
        "in_deg": [5, 5, 5, 3, 5, 1, 1],
        "out_deg": [0, 0, 0, 0, 0, 0, 0],
        "in_kzt": [500_000] * 5 + [20_000, 20_000],
        "out_kzt": [0] * 7,
        "pass_through": [0.0] * 6 + [float("nan")],
        "depth": [1, 1, 1, 2, 0, 4, 2],
        "truncated": [False] * 5 + [True, False],
        "cluster_id": [0] * 7,
        "betweenness": [0.0] * 7,
        "seed_sources_2hop": [1] * 7,
        "fast_pass_share": [0.0] * 7,
    })
    edges = pd.DataFrame({"src": [10, 11, 12], "dst": [20, 20, 20]})
    result = add_roles(metrics, edges).set_index("gid")
    for gid, role in {20: "coordinator", 21: "consolidator", 22: "peripheral", 23: "peripheral"}.items():
        trace = result.loc[gid, "role_explanation"]
        assert trace[-1]["role"] == result.loc[gid, "role"] == role
        assert trace[-1]["matched"] is True
        assert all(not check["matched"] for check in trace[:-1])
        assert [check["rule"] for check in trace] == list(range(1, len(trace) + 1))
    assert "consolidator-candidate payers 0 < 3" in result.loc[21, "role_explanation"][0]["detail"]
    assert "depth 4 > 3" in result.loc[22, "role_explanation"][4]["detail"]
    assert "incoming KZT 20000 < 300000" in result.loc[23, "role_explanation"][4]["detail"]
    assert "observed out/in unknown" in result.loc[23, "role_explanation"][3]["detail"]


def test_priority_explanation_reconstructs_every_score():
    metrics = pd.DataFrame({
        "taint_kzt": [100.0, 300.0, 200.0],
        "seed_sources_2hop": [1, 3, 2],
        "pagerank": [0.1, 0.3, 0.2],
        "betweenness": [0.1, 0.3, 0.2],
        "role": ["peripheral", "coordinator", "terminal"],
        "is_seed": [True, False, False],
        "truncated": [False, True, False],
        "likely_legit_payouts": [False, False, True],
        "common_counterparty": [False, True, True],
        "synchronous_inflow": [False, True, False],
        "fast_pass": [False, True, False],
        "evidence": ["evidence"] * 3,
        "findings": [""] * 3,
    })
    result = add_priority(metrics)
    for row in result.itertuples():
        explanation = row.priority_explanation
        components = explanation["components"]
        assert [part["name"] for part in components] == ["taint", "seed_sources", "pagerank", "betweenness", "role"]
        assert all(math.isclose(part["weight"] * part["value"], part["contribution"]) for part in components)
        subtotal = sum(part["contribution"] for part in components) + explanation["finding_bonus"]
        reconstructed = (subtotal * explanation["seed_multiplier"] * explanation["truncated_multiplier"] /
                         explanation["normalization_divisor"] * explanation["payout_multiplier"])
        assert math.isclose(reconstructed, explanation["score"])
        assert math.isclose(reconstructed, row.priority_score)
    assert result.priority_explanation.iloc[1]["finding_bonus"] == CONFIG.finding_priority_cap
    assert result.priority_explanation.iloc[2]["payout_multiplier"] == CONFIG.payout_priority_multiplier


def test_method_description_tracks_configured_thresholds():
    description = method_description()
    assert len(description["steps"]) == 6
    assert [entry["role"] for entry in description["rules"]] == [
        "coordinator", "consolidator", "distributor", "transit", "terminal", "peripheral"
    ]
    assert str(CONFIG.coordinator_min_consolidators) in description["rules"][0]["rule"]
