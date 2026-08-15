# Ablation experiments

The primary pilot uses 9 profiles, 20 tasks, and 3 paired replicate IDs for a
total of 540 trials. Every profile uses the same guided-agent implementation;
only the seven mechanism flags differ.

Generate or inspect the manifest without API calls:

```bash
uv run hermes-ablation \
  --dataset-path /path/to/terminal-bench/original-tasks \
  --task-file experiments/pilot-tasks.txt \
  --experiment-id ablation-pilot-v1 \
  --dry-run
```

Run or resume the pilot by removing `--dry-run`:

```bash
uv run hermes-ablation \
  --dataset-path /path/to/terminal-bench/original-tasks \
  --task-file experiments/pilot-tasks.txt \
  --experiment-id ablation-pilot-v1
```

Outputs are stored under `runs/experiments/ablation-pilot-v1/`. The runner is
resumable: trials with an existing Terminal-Bench `results.json` are skipped.
`results.csv` contains trial-level outcomes and mechanism events;
`summary.json` contains profile aggregates and paired outcomes against Full.

The numeric `--seed` is sent only when the selected provider advertises seed
support. Otherwise, seed values identify paired independent replicates rather
than deterministic model samples.

Before any trial starts, the runner sends a one-token chat-completion preflight.
It tests provider-appropriate key environment variables and passes only the
selected variable name to child runs. API key values are never written to the
manifest, command line, trajectory, or result files.
