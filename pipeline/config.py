"""All analysis thresholds and weights in one reviewable place."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineConfig:
    expected_nodes: int = 2248
    aggregation_tolerance_kzt: float = 1e-6
    coordinator_min_consolidators: int = 3
    consolidator_min_in: int = 5
    distributor_min_out: int = 10
    distributor_min_ratio: int = 2
    transit_min_ratio: float = 0.8
    transit_max_ratio: float = 1.2
    terminal_max_depth: int = 3
    terminal_max_pass_ratio: float = 0.2
    terminal_min_in: int = 2
    terminal_min_kzt: int = 300_000
    taint_tolerance_kzt: float = 1.0
    taint_max_passes: int = 20
    fast_pass_days: int = 2
    louvain_seed: int = 42
    louvain_resolution: float = 1.0
    layout_seed: int = 42
    layout_iterations: int = 100
    common_counterparty_min_seeds: int = 2
    synchronous_inflow_min_payers: int = 3
    fast_pass_min_share: float = 0.8
    fast_pass_min_kzt: int = 100_000
    scatter_gather_min_branches: int = 3
    scatter_gather_min_edge_kzt: int = 50_000
    twin_min_shared_payers: int = 3
    twin_min_jaccard: float = 0.5
    finding_priority_bonus: float = 0.05
    finding_priority_cap: float = 0.15
    continuation_min_depth: int = 1
    continuation_degree_edges: tuple[int, ...] = (2, 3, 5)
    extension_min_probability: float = 0.5
    skeleton_max_hops: int = 4
    skeleton_top_quantile: float = 0.75
    skeleton_min_inflow_share: float = 0.01
    payout_min_out: int = 10
    payout_busiest_dates: int = 2
    payout_min_date_share: float = 0.5
    payout_max_cv: float = 0.5
    payout_max_taint_share: float = 0.2
    payout_priority_multiplier: float = 0.5
    seed_hub_min_in: int = 5
    seed_hub_min_out: int = 20
    blocking_steps: int = 10
    blocking_max_seconds: float = 60.0
    blocking_candidate_limit: int = 100
    top_count: int = 30
    seed_priority_multiplier: float = 0.6
    truncated_priority_multiplier: float = 0.7
    taint_priority_weight: float = 0.30
    seed_sources_priority_weight: float = 0.20
    pagerank_priority_weight: float = 0.15
    betweenness_priority_weight: float = 0.15
    role_priority_weight: float = 0.20


CONFIG = PipelineConfig()

ROLE_WEIGHTS = {
    "coordinator": 1.0,
    "consolidator": 0.9,
    "distributor": 0.7,
    "transit": 0.6,
    "terminal": 0.4,
    "peripheral": 0.1,
}


def role_rules_markdown(config: PipelineConfig = CONFIG) -> str:
    """Render the README role thresholds from the runtime configuration."""
    rows = method_description(config)["rules"]
    return "| Role | First-matching rule |\n| --- | --- |\n" + "\n".join(
        f"| {entry['role'].title()} | {entry['rule']} |" for entry in rows
    )


def method_description(config: PipelineConfig = CONFIG) -> dict:
    """Describe runtime steps and ordered role rules for the viewer."""
    return {
        "steps": [
            "Load and validate raw nodes, edges, and transactions.",
            "Measure directed flow, network position, timing, and finding signals.",
            f"Propagate observed case-money exposure for up to {config.taint_max_passes} passes.",
            "Assign the first matching role rule to each node.",
            "Detect graph communities and summarize their observed flows.",
            "Rank investigation priorities from weighted signals and uncertainty discounts.",
        ],
        "rules": [
            {"role": "coordinator", "rule": f"Non-seed; receives from >= {config.coordinator_min_consolidators} consolidator candidates (in-degree >= {config.consolidator_min_in}); betweenness breaks score ties"},
            {"role": "consolidator", "rule": f"In-degree >= {config.consolidator_min_in}"},
            {"role": "distributor", "rule": f"Out-degree >= {config.distributor_min_out} and >= {config.distributor_min_ratio} x in-degree (minimum denominator 1)"},
            {"role": "transit", "rule": f"Non-seed; in/out-degree >= 1; observed out/in ratio {config.transit_min_ratio:.1f}-{config.transit_max_ratio:.1f}"},
            {"role": "terminal", "rule": f"Depth <= {config.terminal_max_depth}; incoming > 0; zero outgoing or non-seed out/in < {config.terminal_max_pass_ratio:.1f}; in-degree >= {config.terminal_min_in} or incoming >= {config.terminal_min_kzt:,} KZT"},
            {"role": "peripheral", "rule": "Everything else; cut-off, one-off, isolated seed, or other sub-reason"},
        ],
    }
