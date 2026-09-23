#!/usr/bin/env sh
# Compute official case outputs locally before starting the existing web app.
set -eu
for file in nodes edges transactions; do
  if [ ! -s "data/raw/${file}.parquet" ]; then
    echo "ERROR: missing official input data/raw/${file}.parquet" >&2
    exit 1
  fi
done
if [ ! -s out/nodes_roles.csv ] || [ ! -s out/clusters.csv ] || [ ! -s out/top_nodes.csv ] || [ ! -s out/metrics.csv ] || [ ! -s out/graph.json ]; then
  python -m pipeline.run --data data/raw --out out
fi
exec "$@"
