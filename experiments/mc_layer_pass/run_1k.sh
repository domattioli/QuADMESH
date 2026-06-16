#!/usr/bin/env bash
# Overnight 1000-run MC on WNAT_Hagen, then analyze + figures + commit/push.
# Memory-safe: the harness accumulates per-triangle counts incrementally
# (routed arrays are discarded after np.add.at) and uses imap_unordered with
# chunksize=1, so peak memory is O(workers * mesh), not O(runs).
set -uo pipefail
cd /home/user/QuADMESH
. .venv/bin/activate

TAG=wnat_hagen_1k
MESH=/tmp/WNAT_Hagen.14
LOG=experiments/mc_layer_pass/results/${TAG}_run.log

echo "=== 1000-run MC start $(date -u) ==="
python experiments/mc_layer_pass/run_mc.py --mesh "$MESH" --runs 1000 --workers 4 --tag "$TAG"
python experiments/mc_layer_pass/analyze.py --tag "$TAG"
python experiments/mc_layer_pass/explain_leftovers.py --tag "$TAG"
python experiments/mc_layer_pass/pubfigs.py --tag "$TAG"

git add experiments/mc_layer_pass/figures/${TAG}_*.png \
        experiments/mc_layer_pass/results/${TAG}_per_run.csv \
        experiments/mc_layer_pass/results/${TAG}_correlations.csv \
        experiments/mc_layer_pass/results/${TAG}_group_means.csv \
        experiments/mc_layer_pass/results/${TAG}_by_layer.csv \
        experiments/mc_layer_pass/results/${TAG}_leftover_motifs.csv \
        experiments/mc_layer_pass/results/${TAG}_deconfounded_corr.csv \
        experiments/mc_layer_pass/results/${TAG}_explain_summary.json \
        experiments/mc_layer_pass/results/${TAG}_meta.json 2>/dev/null
git commit -m "chore: add 1000-run WNAT_Hagen MC results (overnight)" || echo "nothing to commit"
for i in 1 2 3 4; do git push && break || sleep $((2**i)); done

echo "=== RUN_1K_COMPLETE $(date -u) ==="
