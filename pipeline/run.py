"""Command-line entry point for a complete offline pipeline run."""

import argparse
import time
from pathlib import Path

from pipeline.blocking import blocking_plan, blocking_summary
from pipeline.clusters import add_clusters, assign_clusters
from pipeline.config import CONFIG
from pipeline.export import write_outputs
from pipeline.continuation import add_continuation
from pipeline.features import compute_features
from pipeline.findings import add_findings, add_payout_flag, add_seed_hub_flag, FINDING_TEXT
from pipeline.load import load_data
from pipeline.priority import add_priority
from pipeline.roles import add_roles
from pipeline.taint import add_taint
from pipeline.skeleton import add_skeleton


def run(data: str = "data/raw", out: str = "out") -> None:
    started = time.monotonic()
    print(f"Coordinator threshold: >= {CONFIG.coordinator_min_consolidators} consolidator candidates")
    print(f"Scatter/gather thresholds: >= {CONFIG.scatter_gather_min_branches} distinct first intermediaries; "
          f"every branch edge >= {CONFIG.scatter_gather_min_edge_kzt:,} KZT; 2-3 hops")
    nodes, edges, transactions = load_data(data)
    metrics, graph = compute_features(nodes, edges, transactions)
    metrics = add_taint(metrics, edges)
    metrics, _ = assign_clusters(metrics, edges, graph)
    metrics = add_roles(metrics, edges)
    metrics = add_findings(metrics, transactions, graph)
    metrics = add_payout_flag(metrics, transactions)
    metrics = add_seed_hub_flag(metrics)
    metrics = add_continuation(metrics)
    metrics = add_priority(metrics)
    metrics, clusters, projected = add_clusters(metrics, edges, graph)
    metrics, skeleton_edges = add_skeleton(metrics, edges, graph)
    Path(out).mkdir(parents=True, exist_ok=True)
    skeleton_edges.to_csv(Path(out) / "skeleton_edges.csv", index=False, float_format="%.12g")
    plan, limited = blocking_plan(metrics, edges)
    plan.to_csv(Path(out) / "blocking_plan.csv", index=False, float_format="%.12g")
    write_outputs(metrics, clusters, edges, projected, out)
    counts = metrics.role.value_counts()
    for role in ("coordinator", "consolidator", "distributor", "transit", "terminal", "peripheral"):
        count = int(counts.get(role, 0))
        print(f"{role}: {count}")
        if count == 0 or count > 500:
            print(f"Warning: {role} count is outside the expected range")
    for flag in (*FINDING_TEXT, "likely_legit_payouts", "seed_hub"):
        print(f"{flag}: {int(metrics[flag].sum())}")
    if limited:
        print("Blocking candidate search exceeded 60 seconds; used top 100 by priority.")
    print(blocking_summary(plan))
    print(f"Analyzed {len(nodes)} nodes, {len(edges)} edges and {len(clusters)} clusters in {time.monotonic() - started:.2f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze the supplied money-transfer graph")
    parser.add_argument("--data", default="data/raw", help="Directory containing three case Parquet files")
    parser.add_argument("--out", default="out", help="Output directory for CSV tables and graph JSON")
    arguments = parser.parse_args()
    run(arguments.data, arguments.out)


if __name__ == "__main__":
    main()
