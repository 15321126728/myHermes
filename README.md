# Replayable Hermes Agent

A focused, installable extraction of the Hermes agent stack developed on top
of [Terminal-Bench](https://github.com/laude-institute/terminal-bench).

## Architecture

```text
Terminus2
  -> ReplayableHermesAgent
    -> IntervenedTerminusAgent
      -> GuidedInterventionAgent
```

- `ReplayableHermesAgent` records and replays model trajectories.
- `IntervenedTerminusAgent` adds schedules, triggers, forced commands, and
  optional validation feedback.
- `GuidedInterventionAgent` adds process guidance, cognitive-error detection,
  and adaptive episode management.

This repository intentionally excludes benchmark tasks, run logs, model
caches, experiment reports, and API credentials.

For a detailed comparison with the classic Terminus2 baseline, including
limitations and validation evidence, see [IMPROVEMENTS.md](IMPROVEMENTS.md).

## Install

Requirements: Python 3.12+, `uv`, Docker with Compose, and a local
Terminal-Bench task dataset.

```bash
git clone --branch agent-only --single-branch \
  https://github.com/15321126728/myHermes.git
cd myHermes
uv sync --dev
cp .env.example .env
```

Set `DEEPSEEK_API_KEY` or `OPENAI_API_KEY` in your environment. Never commit
the populated `.env` file.

## Run

Pass the path to a Terminal-Bench-compatible dataset containing the selected
task directory:

```bash
export DEEPSEEK_API_KEY="your-key"

uv run hermes-agent \
  --dataset-path /path/to/terminal-bench/original-tasks \
  --task hello-world \
  --agent replayable-hermes
```

Use an intervention or replay an existing trajectory:

```bash
uv run hermes-agent \
  --dataset-path /path/to/terminal-bench/original-tasks \
  --task hello-world \
  --agent intervened-terminus \
  --intervention "Inspect the current state before continuing." \
  --replay-path runs/previous/trajectory.json \
  --replay-until 1
```

Generated trajectories are written below `runs/<run-id>/`.

## Development

```bash
uv sync --dev
uv run ruff check .
uv run pytest
```

## License and attribution

Licensed under Apache License 2.0. This project contains adapted components
from Terminal-Bench and preserves its license. See `LICENSE`.
