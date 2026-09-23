"""End-to-end checks for the offline Money Graph pipeline."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import time
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from pipeline import load as load_module
from pipeline.config import CONFIG
from pipeline.features import _fast_pass_share
from pipeline.taint import add_taint


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw"
ROLES = {
    "coordinator",
    "consolidator",
    "distributor",
    "transit",
    "terminal",
    "peripheral",
}
CSV_NAMES = ("nodes_roles.csv", "clusters.csv", "top_nodes.csv", "metrics.csv",
             "extension_requests.csv", "skeleton_edges.csv", "blocking_plan.csv", "twin_groups.csv")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return list(reader.fieldnames or []), list(reader)


def numeric_score(value: str) -> float:
    score = float(value)
    assert math.isfinite(score)
    assert 0 <= score <= 1
    return score


@pytest.fixture(scope="session")
def pipeline_outputs(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    outputs = (tmp_path_factory.mktemp("pipeline-first"), tmp_path_factory.mktemp("pipeline-second"))
    for output in outputs:
        start = time.monotonic()
        result = subprocess.run(
            [sys.executable, "-m", "pipeline.run", "--data", str(DATA), "--out", str(output)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        duration = time.monotonic() - start
        assert result.returncode == 0, f"Pipeline failed:\n{result.stdout}\n{result.stderr}"
        assert duration < 300, f"Pipeline took {duration:.1f}s; required runtime is under five minutes"
        for name in (*CSV_NAMES, "graph.json"):
            assert (output / name).is_file(), f"Missing pipeline output: {name}"
    return outputs


def test_nodes_roles_and_metrics_cover_input(pipeline_outputs: tuple[Path, Path]) -> None:
    output, _ = pipeline_outputs
    header, roles = read_csv(output / "nodes_roles.csv")
    assert header == ["gid", "role", "role_score", "cluster_id", "priority_score", "evidence"]

    input_gids = {str(int(gid)) for gid in pd.read_parquet(DATA / "nodes.parquet")["gid"]}
    gids = [row["gid"] for row in roles]
    assert len(input_gids) == len(roles) == 2248
    assert len(set(gids)) == len(gids)
    assert set(gids) == input_gids

    for row in roles:
        assert row["role"] in ROLES
        assert row["cluster_id"] != ""
        numeric_score(row["role_score"])
        numeric_score(row["priority_score"])
        assert 0 < len(row["evidence"].strip()) <= 200

    metric_header, metrics = read_csv(output / "metrics.csv")
    required_metrics = {
        "gid", "in_deg", "out_deg", "in_kzt", "out_kzt", "in_tx", "out_tx",
        "depth", "is_seed", "pass_through", "truncated", "seed_payers_direct",
        "seed_sources_2hop", "pagerank", "betweenness", "fast_pass_share",
        "taint_kzt", "taint_share", "peripheral_reason",
    }
    assert required_metrics <= set(metric_header)
    metric_gids = [row["gid"] for row in metrics]
    assert len(metric_gids) == len(set(metric_gids)) == 2248
    assert set(metric_gids) == input_gids

    roles_by_gid = {row["gid"]: row for row in roles}
    for row in metrics:
        if int(row["depth"]) == 4 and int(row["out_deg"]) == 0:
            assert roles_by_gid[row["gid"]]["role"] != "terminal"


def test_clusters_cover_every_node(pipeline_outputs: tuple[Path, Path]) -> None:
    output, _ = pipeline_outputs
    _, roles = read_csv(output / "nodes_roles.csv")
    header, clusters = read_csv(output / "clusters.csv")
    assert {"cluster_id", "n_nodes", "n_seed", "sum_kzt_internal", "top_gids", "hypothesis"} <= set(header)

    cluster_ids = [row["cluster_id"] for row in clusters]
    assert len(cluster_ids) == len(set(cluster_ids))
    assert all(row["hypothesis"].strip() for row in clusters)
    assert {row["cluster_id"] for row in roles} == set(cluster_ids)
    assert sum(int(row["n_nodes"]) for row in clusters) == len(roles)
    member_counts = Counter(row["cluster_id"] for row in roles)
    for cluster in clusters:
        count = member_counts[cluster["cluster_id"]]
        assert int(cluster["n_nodes"]) == count
        assert 0 <= int(cluster["n_seed"]) <= count


def test_top_nodes_are_ranked_and_explained(pipeline_outputs: tuple[Path, Path]) -> None:
    output, _ = pipeline_outputs
    _, roles = read_csv(output / "nodes_roles.csv")
    header, top = read_csv(output / "top_nodes.csv")
    assert header == ["rank", "gid", "role", "priority_score", "why"]
    assert 20 <= len(top) <= 30
    assert [int(row["rank"]) for row in top] == list(range(1, len(top) + 1))
    assert len({row["gid"] for row in top}) == len(top)
    assert all(row["why"].strip() for row in top)
    scores = [numeric_score(row["priority_score"]) for row in top]
    assert scores == sorted(scores, reverse=True)

    roles_by_gid = {row["gid"]: row for row in roles}
    top_gids = {row["gid"] for row in top}
    assert scores[-1] >= max(
        float(row["priority_score"]) for row in roles if row["gid"] not in top_gids
    )
    for row in top:
        assert row["gid"] in roles_by_gid
        assert row["role"] == roles_by_gid[row["gid"]]["role"]
        assert math.isclose(float(row["priority_score"]), float(roles_by_gid[row["gid"]]["priority_score"]))


def test_graph_json_matches_exports(pipeline_outputs: tuple[Path, Path]) -> None:
    output, _ = pipeline_outputs
    _, roles = read_csv(output / "nodes_roles.csv")
    graph = json.loads((output / "graph.json").read_text(encoding="utf-8"))
    assert {"nodes", "edges", "roles_count", "generated_at"} <= set(graph)
    assert len(graph["nodes"]) == len(roles) == 2248
    assert len(graph["edges"]) == 3119
    graph_gids = {node["id"] for node in graph["nodes"]}
    assert graph_gids == {row["gid"] for row in roles}
    assert all(isinstance(node["id"], str) for node in graph["nodes"])
    node_fields = {
        "id", "role", "cluster", "priority", "seed", "depth", "truncated", "x", "y",
        "evidence", "in_kzt", "out_kzt", "in_deg", "out_deg",
    }
    assert all(node_fields <= set(node) for node in graph["nodes"])
    assert all({"source", "target", "sum_kzt", "n_tx"} <= set(edge) for edge in graph["edges"])
    assert all(edge["source"] in graph_gids and edge["target"] in graph_gids for edge in graph["edges"])
    assert sum(graph["roles_count"].values()) == 2248


def test_repeated_runs_produce_identical_csvs(pipeline_outputs: tuple[Path, Path]) -> None:
    first, second = pipeline_outputs
    for name in CSV_NAMES:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_taint_dilutes_external_outflow_and_keeps_seed_share() -> None:
    metrics = pd.DataFrame(
        {
            "gid": [1, 2, 3, 4],
            "is_seed": [True, False, False, True],
            "in_kzt": [50, 100, 200, 0],
            "out_kzt": [100, 200, 50, 0],
        }
    )
    edges = pd.DataFrame(
        {"src": [1, 2, 3], "dst": [2, 3, 1], "sum_kzt": [100, 200, 50]}
    )
    result = add_taint(metrics, edges).set_index("gid")
    assert result.loc[1, "taint_share"] == 1.0  # Seeds retain their source policy after incoming transfers.
    assert result.loc[4, "taint_share"] == 1.0  # An isolated seed is still a source.
    assert result.loc[2, "taint_share"] == pytest.approx(0.5)
    assert result.loc[3, "taint_kzt"] == pytest.approx(100.0)
    assert result.loc[3, "taint_share"] == pytest.approx(0.5)
    assert all(math.isfinite(value) for value in result["taint_kzt"])


def test_taint_cycle_is_bounded() -> None:
    metrics = pd.DataFrame(
        {
            "gid": [1, 2, 3],
            "is_seed": [True, False, False],
            "in_kzt": [0, 150, 100],
            "out_kzt": [100, 100, 50],
        }
    )
    edges = pd.DataFrame(
        {"src": [1, 2, 3], "dst": [2, 3, 2], "sum_kzt": [100, 100, 50]}
    )
    start = time.monotonic()
    result = add_taint(metrics, edges).set_index("gid")
    assert time.monotonic() - start < 2
    assert all(math.isfinite(value) for value in result["taint_kzt"])
    assert all(0 <= value <= 1 for value in result["taint_share"])
    assert result.loc[2, "taint_kzt"] > 100
    assert result.loc[3, "taint_kzt"] > 0


def test_fast_pass_share_includes_exact_two_day_boundary() -> None:
    nodes = pd.DataFrame({"gid": [1, 2, 3, 4]})
    transactions = pd.DataFrame(
        {
            "src": [1, 2, 2, 2],
            "dst": [2, 3, 3, 3],
            "date": pd.to_datetime(
                ["2026-07-01 12:00:00", "2026-07-03 12:00:00",
                 "2026-07-03 12:00:01", "2026-07-01 11:59:59"]
            ),
            "sum_kzt": [100, 20, 30, 50],
        }
    )
    shares = _fast_pass_share(nodes, transactions)
    assert shares[2] == pytest.approx(0.2)
    assert shares[3] == 0.0
    assert math.isnan(shares[4])


@pytest.mark.parametrize("field,wrong_value", [("sum_kzt", 31), ("n_tx", 1)])
def test_loader_rejects_edge_aggregation_mismatch(
    monkeypatch: pytest.MonkeyPatch, field: str, wrong_value: int
) -> None:
    nodes = pd.DataFrame({"gid": [1, 2, 3], "depth": [0, 1, 2], "is_seed": [True, False, False]})
    edges = pd.DataFrame(
        {"src": [1, 2], "dst": [2, 3], "sum_kzt": [30, 10], "n_tx": [2, 1], "depth": [1, 2]}
    )
    transactions = pd.DataFrame(
        {
            "src": [1, 1, 2], "dst": [2, 2, 3],
            "date": pd.to_datetime(["2026-07-01", "2026-07-02", "2026-07-03"]),
            "sum_kzt": [10, 20, 10],
        }
    )
    frames = {"nodes.parquet": nodes, "edges.parquet": edges, "transactions.parquet": transactions}
    monkeypatch.setattr(load_module, "CONFIG", replace(load_module.CONFIG, expected_nodes=3))
    monkeypatch.setattr(load_module.pd, "read_parquet", lambda path: frames[path.name].copy())
    clean_nodes, clean_edges, clean_transactions = load_module.load_data("unused")
    assert (len(clean_nodes), len(clean_edges), len(clean_transactions)) == (3, 2, 3)

    edges.loc[0, field] = wrong_value
    with pytest.raises(ValueError, match="Edges disagree with transaction sums/counts"):
        load_module.load_data("unused")


def test_loader_accepts_float_roundoff_but_rejects_real_difference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    nodes = pd.DataFrame({"gid": [1, 2, 3], "depth": [0, 1, 2], "is_seed": [True, False, False]})
    edges = pd.DataFrame(
        {"src": [1], "dst": [2], "sum_kzt": [30_000.30000000005], "n_tx": [2], "depth": [1]}
    )
    transactions = pd.DataFrame(
        {
            "src": [1, 1], "dst": [2, 2],
            "date": pd.to_datetime(["2026-07-01", "2026-07-02"]),
            "sum_kzt": [10_000.1, 20_000.2],
        }
    )
    frames = {"nodes.parquet": nodes, "edges.parquet": edges, "transactions.parquet": transactions}
    monkeypatch.setattr(load_module, "CONFIG", replace(load_module.CONFIG, expected_nodes=3))
    monkeypatch.setattr(load_module.pd, "read_parquet", lambda path: frames[path.name].copy())
    assert len(load_module.load_data("unused")[1]) == 1

    edges.loc[0, "sum_kzt"] += 0.01
    with pytest.raises(ValueError, match="Edges disagree with transaction sums/counts"):
        load_module.load_data("unused")


def test_findings_artifacts_and_viewer_integration(pipeline_outputs):
    from app.api.viewer import OutputStore

    output, _ = pipeline_outputs
    metrics = pd.read_csv(output / "metrics.csv", dtype={"gid": str})
    flags = ["common_counterparty", "synchronous_inflow", "fast_pass", "scatter_gather",
             "likely_legit_payouts", "seed_hub", "in_skeleton"]
    assert all(metrics[flag].dtype == bool for flag in flags)
    coordinators = metrics[metrics.role.eq("coordinator")]
    consolidators = metrics[metrics.role.eq("consolidator")]
    assert 5 <= len(coordinators) <= 30
    assert len(consolidators) >= 30
    assert metrics.scatter_gather.sum() < 100
    assert CONFIG.coordinator_min_consolidators == 3
    assert CONFIG.scatter_gather_min_branches == 3
    assert CONFIG.scatter_gather_min_edge_kzt == 50_000
    assert not coordinators.is_seed.any()
    assert coordinators.consolidator_payers.ge(CONFIG.coordinator_min_consolidators).all()
    assert metrics.loc[~metrics.is_seed & metrics.consolidator_payers.ge(
        CONFIG.coordinator_min_consolidators), "role"].eq("coordinator").all()
    extensions = pd.read_csv(output / "extension_requests.csv", dtype={"gid": str})
    assert set(extensions.gid) <= set(metrics.loc[metrics.truncated, "gid"])
    assert extensions.p_continues.ge(.5).all()
    plan = pd.read_csv(output / "blocking_plan.csv", dtype={"gid": str})
    assert len(plan) == plan.gid.nunique() == 10
    assert not set(plan.gid) & set(metrics.loc[metrics.is_seed, "gid"])
    assert plan.cut_share_cumulative.between(0, 1).all()
    assert plan.cut_share_cumulative.is_monotonic_increasing
    snapshot = OutputStore(output).load()
    flagged = metrics.loc[metrics.common_counterparty, "gid"].iloc[0]
    assert isinstance(snapshot["nodes"][flagged]["findings"], str)
    assert snapshot["nodes"][flagged]["common_counterparty"] is True
    graph = json.loads((output / "graph.json").read_text())
    by_gid = metrics.set_index("gid")
    for node in graph["nodes"]:
        assert node["skeleton"] == bool(by_gid.loc[node["id"], "in_skeleton"])
        assert node["level"] == int(by_gid.loc[node["id"], "hierarchy_level"])


def test_official_twins_are_symmetric_and_groups_retain_exact_ids(pipeline_outputs):
    output, _ = pipeline_outputs
    header, groups = read_csv(output / "twin_groups.csv")
    assert header == ["group_id", "gids", "shared_payers", "total_in_kzt", "hypothesis"]
    _, metrics = read_csv(output / "metrics.csv")
    flagged = {row["gid"]: row for row in metrics if row["shared_sources_twin"] == "True"}
    assert len(flagged) == 37 and len(groups) == 9
    assert sum(len(json.loads(row["twin_gids"])) for row in flagged.values()) == 90
    for gid, row in flagged.items():
        for twin in json.loads(row["twin_gids"]):
            assert isinstance(twin, str) and gid in json.loads(flagged[twin]["twin_gids"])
            assert json.loads(row["twin_shared_payers"])[twin] >= 3
            assert flagged[twin]["twin_group"] == row["twin_group"]
    a, b = "100000003115284100", "100000006889963100"
    assert json.loads(flagged[a]["twin_shared_payers"])[b] == 4
    exported = {gid for group in groups for gid in json.loads(group["gids"])}
    assert exported == set(flagged)
