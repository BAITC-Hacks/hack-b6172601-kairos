"""Deterministic circle separation for exported graph coordinates."""

import math
from collections import defaultdict


def remove_overlaps(positions, priorities):
    """Push nearby circles apart, then place any residual collisions in free space."""
    points = {gid: [float(x), float(y)] for gid, (x, y) in positions.items()}
    radii = {gid: 3 + 9 * float(priorities[gid]) for gid in points}
    cell = 26.0
    gids = sorted(points)
    for _ in range(200):
        grid = defaultdict(list)
        for gid in gids:
            x, y = points[gid]
            grid[(math.floor(x / cell), math.floor(y / cell))].append(gid)
        changed = False
        for gid in gids:
            x, y = points[gid]
            gx, gy = math.floor(x / cell), math.floor(y / cell)
            for ix in range(gx - 1, gx + 2):
                for iy in range(gy - 1, gy + 2):
                    for other in grid[(ix, iy)]:
                        if other <= gid:
                            continue
                        dx, dy = points[other][0] - points[gid][0], points[other][1] - points[gid][1]
                        distance = math.hypot(dx, dy)
                        minimum = radii[gid] + radii[other] + 2.001
                        if distance >= minimum:
                            continue
                        changed = True
                        ux, uy = (dx / distance, dy / distance) if distance else (1.0, 0.0)
                        shift = (minimum - distance) / 2
                        points[gid][0] -= ux * shift
                        points[gid][1] -= uy * shift
                        points[other][0] += ux * shift
                        points[other][1] += uy * shift
        if not changed:
            break
    # Dense coincident inputs may not converge within 200 passes. This final
    # spatial placement guarantees the contract without discarding any node.
    grid = defaultdict(list)
    result = {}
    for gid in sorted(gids, key=lambda gid: (-priorities[gid], gid)):
        origin = points[gid]
        x, y = origin
        attempt = 0
        while True:
            gx, gy = math.floor(x / cell), math.floor(y / cell)
            neighbours = (other for ix in range(gx - 1, gx + 2) for iy in range(gy - 1, gy + 2)
                          for other in grid[(ix, iy)])
            if all(math.hypot(x - result[other][0], y - result[other][1]) >= radii[gid] + radii[other] + 2
                   for other in neighbours):
                break
            attempt += 1
            angle, distance = attempt * 2.399963229728653, cell * math.sqrt(attempt)
            x, y = origin[0] + math.cos(angle) * distance, origin[1] + math.sin(angle) * distance
        result[gid] = (x, y)
        grid[(gx, gy)].append(gid)
    return result
