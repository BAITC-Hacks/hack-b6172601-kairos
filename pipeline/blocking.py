"""Counterfactual greedy removals under the observed haircut-taint model."""
import time

import numpy as np
import pandas as pd

from pipeline.config import CONFIG

COLUMNS = ["step", "gid", "role", "cut_share_cumulative"]


class TaintSimulation:
    """Reuse indexed edges; preserve original denominators under every removal."""

    def __init__(self, metrics: pd.DataFrame, edges: pd.DataFrame):
        self.gids = metrics.gid.to_numpy(dtype="int64")
        indices = {int(gid): index for index, gid in enumerate(self.gids)}
        self.src = np.asarray([indices[int(gid)] for gid in edges.src], dtype=int)
        self.dst = np.asarray([indices[int(gid)] for gid in edges.dst], dtype=int)
        self.amounts = edges.sum_kzt.to_numpy(dtype=float)
        self.seeds = metrics.is_seed.to_numpy(dtype=bool)
        self.denominator = np.maximum(metrics.in_kzt.to_numpy(dtype=float),
                                      metrics.out_kzt.to_numpy(dtype=float))
        self.has_outgoing = np.bincount(self.src, minlength=len(metrics)) > 0

    def trace(self, active: np.ndarray) -> np.ndarray:
        share = (self.seeds & active).astype(float)
        amounts = self.amounts * (active[self.src] & active[self.dst])
        taint = np.zeros(len(active))
        # Fixed passes make all counterfactuals comparable, including cycles.
        for _ in range(CONFIG.taint_max_passes):
            taint = np.bincount(self.dst, weights=amounts * share[self.src], minlength=len(active))
            share = np.minimum(1.0, np.divide(
                taint, self.denominator, out=np.zeros_like(taint), where=self.denominator > 0))
            share[self.seeds & active] = 1.0
            share[~active] = 0.0
        return taint


def blocking_plan(metrics: pd.DataFrame, edges: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    model = TaintSimulation(metrics, edges)
    positions = {int(gid): index for index, gid in enumerate(model.gids)}
    ranked = metrics.loc[~metrics.is_seed].sort_values(["priority_score", "gid"], ascending=[False, True])
    candidates = [positions[int(gid)] for gid in ranked.gid]
    roles = dict(zip(metrics.gid, metrics.role))
    baseline = model.trace(np.ones(len(metrics), dtype=bool))
    baseline_total = float(baseline.sum())

    def greedy(pool: list[int], deadline: float | None):
        active = np.ones(len(metrics), dtype=bool)
        current = baseline.copy()
        rows = []
        for step in range(1, min(CONFIG.blocking_steps, len(pool)) + 1):
            best, best_gain, best_trace = None, -1.0, None
            current_total = float(current.sum())
            for candidate in pool:
                if deadline is not None and time.monotonic() >= deadline:
                    return None
                if not active[candidate]:
                    continue
                if not model.has_outgoing[candidate] or current[candidate] == 0:
                    # With fixed denominators, removing a sink cannot affect others.
                    trial = current.copy()
                    trial[candidate] = 0.0
                else:
                    active[candidate] = False
                    trial = model.trace(active)
                    active[candidate] = True
                gain = max(0.0, current_total - current[candidate] - float(trial.sum()))
                # Pool order resolves exact ties by priority, then exact integer gid.
                if gain > best_gain:
                    best, best_gain, best_trace = candidate, gain, trial
            if best is None:
                break
            active[best] = False
            current = best_trace
            cut = (baseline_total - float(current.sum())) / baseline_total if baseline_total else 0.0
            gid = int(model.gids[best])
            rows.append({"step": step, "gid": gid, "role": roles[gid],
                         "cut_share_cumulative": min(1.0, max(0.0, cut))})
        return pd.DataFrame(rows, columns=COLUMNS)

    plan = greedy(candidates, time.monotonic() + CONFIG.blocking_max_seconds)
    limited = plan is None
    if limited:
        plan = greedy(candidates[:CONFIG.blocking_candidate_limit], None)
    return plan, limited


def blocking_summary(plan: pd.DataFrame) -> str:
    share = float(plan.cut_share_cumulative.iloc[-1]) if len(plan) else 0.0
    return f"Blocking these {len(plan)} accounts would cut {share:.1%} of case money flow in the observed graph."
