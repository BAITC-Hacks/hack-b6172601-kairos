"""Conservative amount-weighted tracing from known seed accounts."""

import numpy as np
import pandas as pd

from pipeline.config import CONFIG


def add_taint(metrics: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    result = metrics.copy()
    gids = result.gid.to_numpy(dtype="int64")
    indices = {int(gid): i for i, gid in enumerate(gids)}
    src = np.asarray([indices[int(gid)] for gid in edges.src], dtype=int)
    dst = np.asarray([indices[int(gid)] for gid in edges.dst], dtype=int)
    amounts = edges.sum_kzt.to_numpy(dtype=float)
    seeds = result.is_seed.to_numpy(dtype=bool)
    denominator = np.maximum(result.in_kzt.to_numpy(dtype=float), result.out_kzt.to_numpy(dtype=float))
    taint = np.zeros(len(result), dtype=float)
    share = seeds.astype(float)
    for _ in range(CONFIG.taint_max_passes):
        updated = np.bincount(dst, weights=amounts * share[src], minlength=len(result))
        updated_share = np.minimum(1.0, np.divide(updated, denominator, out=np.zeros_like(updated), where=denominator > 0))
        updated_share[seeds] = 1.0
        difference = np.max(np.abs(updated - taint))
        taint, share = updated, updated_share
        if difference < CONFIG.taint_tolerance_kzt:
            break
    result["taint_kzt"] = taint
    result["taint_share"] = share
    return result
