# Improvements over the classic Terminus2 baseline

This document describes how this repository extends the classic Terminal-Bench
`Terminus2` loop. It separates general agent capabilities from experimental or
task-specific strategies so that results are not overstated.

## Baseline

The classic baseline follows a direct loop:

1. Render the task and current terminal state into a prompt.
2. Ask the model for structured commands.
3. Parse and execute those commands in the terminal.
4. Feed terminal output into the next model turn.
5. Require a second completion confirmation before grading.

This is a strong simple baseline, but it does not provide first-class
trajectory replay, scheduled interventions, process-level failure diagnosis,
or portable experiment artifacts.

## Summary of changes

| Area | Classic baseline | This project | Intended benefit |
| --- | --- | --- | --- |
| Trajectories | Episode logs only | Structured prompts, responses, commands, outputs, and completion state | Reproducible debugging and comparison |
| Replay | No first-class replay boundary | Replay a recorded prefix, then resume model sampling | Controlled counterfactual experiments |
| Intervention | Model proceeds without an external policy | Scheduled, triggered, pre-episode, inject, overwrite, and history-truncation interventions | Recover from known failure modes |
| Loop detection | No explicit repetition policy | Detect repeated commands and analysis-only loops | Reduce unproductive token use |
| Process guidance | Terminal output is the main feedback | Cognitive, execution-layer, and ternary process diagnosis | Give feedback about how the process is failing |
| Episode budget | Fixed maximum | Optional adaptive extension based on recoverability and progress | Avoid stopping recoverable trajectories too early |
| Parsing | Structured response parser | Markdown-fence stripping and tolerant surrounding-text handling | Fewer parser deadlocks with chat-oriented models |
| LLM calls | Provider defaults | Explicit timeout, bounded retries, proxy visibility, and DeepSeek response-format fallback | Faster and clearer recovery from API failures |
| Completion | Model confirmation | Optional deterministic output-artifact gate | Prevent premature completion when required files are missing |
| Portability | Usually run inside the benchmark source tree | Installable package, dataset-path CLI, environment-based credentials, portable artifact paths | Easier reuse from a clean clone |

## 1. Replayable trajectories

`ReplayableHermesAgent` records each episode as structured data:

- prompt and raw model response;
- normalized command batch and command duration;
- terminal output and parser feedback;
- replay status and completion state.

A previous trajectory can be replayed up to `replay_until_episode`. The agent
then switches back to live model sampling. This supports controlled experiments
where the prefix is held constant and only a later intervention changes.

Relevant code:

- `src/hermes_agent/replayable_hermes.py`
- `src/hermes_agent/replay_support.py`

## 2. Deterministic and conditional intervention

`IntervenedTerminusAgent` adds several intervention mechanisms:

- episode-based schedules;
- regex triggers over terminal output;
- injection before an episode or after replay;
- assistant-message overwrite and user-message injection;
- forced command batches for controlled experiments;
- one-shot trigger tracking to prevent repeated firing;
- trajectory records for every intervention decision.

It also detects repeated commands and analysis-only behavior. A detected loop
can truncate stale history and inject a recovery instruction rather than letting
the same behavior continue indefinitely.

Relevant code:

- `src/hermes_agent/intervened_terminus.py`

## 3. Process-guided recovery

`GuidedInterventionAgent` and `ProcessGuidanceEngine` move beyond fixed answer
hints. The implemented mechanism matrix is:

| Mechanism | Runtime behavior |
| --- | --- |
| Five cognitive errors | Detects task misunderstanding, wrong tool choice, format misunderstanding, premature success, and multi-episode analysis paralysis from commands, terminal output, and the model response |
| Seven diagnosis layers | Locates signals in execution, tool, context, lifecycle, observability, validation, and governance layers |
| Ternary feedback | Emits `CORRECT`, `RECOVERABLE`, or `IRRECOVERABLE`; one irrecoverable trajectory can be re-grounded with stale chat history removed |
| Adaptive episodes | Extends only at the current budget boundary when at least three recent episodes contain measured productive progress; analysis loops do not extend and extensions are capped |
| Runtime verification | Extracts declared output artifacts and checks them inside the container after every episode with a non-empty-file gate; missing artifacts block completion |
| Knowledge supply | Announces a real container knowledge document before the first live turn and repeats the hint only when knowledge-gap language is detected |
| Comprehension check | Asks task-specific or contract-derived questions before the first live turn and deterministically checks required answer keywords |

The CLI passes the selected task ID and actual episode budget into the guided
agent automatically. Three bundled benchmark tasks expose known knowledge-file
locations; other datasets can use `--knowledge-file` explicitly. The agent
checks that the document exists and is non-empty before mentioning it.

Relevant code:

- `src/hermes_agent/guided_intervention.py`
- `src/hermes_agent/process_guidance.py`

## 4. Parser and model-call robustness

The JSON parser strips common Markdown code fences before parsing and tolerates
harmless conversational text around a valid JSON object. This specifically
targets models that return structured output inside a fenced code block.

The LiteLLM adapter adds:

- an explicit request timeout;
- bounded retry delays;
- proxy detection in logs;
- a textual JSON fallback for DeepSeek-compatible endpoints that reject native
  `response_format` parameters.

These changes improve failure recovery and diagnostics. They do not guarantee
that every malformed model response can be repaired.

Relevant code:

- `src/hermes_agent/terminus_json_plain_parser.py`
- `src/hermes_agent/lite_llm.py`
- `src/hermes_agent/terminus.py`

## 5. Progress and completion controls

The extended Terminus loop includes:

- episode and substantive-action progress context;
- detection of excessive analysis relative to concrete actions;
- shorter terminal-output windows to reduce context growth;
- simplified handoff summarization;
- an optional deterministic gate that checks required output artifacts before
  accepting completion.

The deterministic gate extracts output paths from the task instruction. It is
useful for explicit file-producing tasks, but falls back to normal completion
when the instruction does not define a concrete artifact.

Relevant code:

- `src/hermes_agent/terminus.py`
- `src/hermes_agent/task_contract.py`

## 6. Optional task-specific validation

The repository retains two experimental validators:

- `oracle_distance.py` computes dense progress signals for the DNA primer task;
- `dockerless_validator.py` statically checks primer structure without invoking
  the full task judge.

These modules demonstrate how domain validators can provide denser feedback,
but they are not general-purpose Terminal-Bench improvements. They are disabled
by default and should be evaluated separately from the generic agent stack.

## 7. Portability and release safety

The extracted package adds operational improvements that are independent of
agent reasoning quality:

- standard `src/` Python package layout;
- `uv` lock file and reproducible installation;
- `hermes-agent` CLI with explicit dataset and output paths;
- no repository-specific absolute paths;
- API credentials read only from environment variables;
- trajectories and local `.env` files excluded from Git.

## Evidence available today

The current release has the following verified evidence:

- clean installation against the published `terminal-bench==0.2.18` package;
- Ruff static checks pass;
- package tests pass (`16 passed`), including direct tests for all seven guidance
  mechanisms and CLI wiring;
- source distribution and wheel build successfully;
- a real Docker-backed `hello-world` run completed with `1/1` resolved and
  `100%` accuracy using the extracted package.

This proves packaging, imports, Docker integration, model invocation,
trajectory persistence, and basic task execution work end to end.

## What is not yet proven

The `hello-world` result does not establish a statistically significant
improvement over classic Terminus2. A defensible effectiveness claim requires:

- the same task set, model, temperature, and episode budget;
- multiple seeds or repeated trials;
- baseline versus replay/intervention/guidance ablations;
- success rate, token usage, wall time, parser failure rate, and intervention
  frequency;
- separate reporting for generic policies and task-specific validators.

Until those experiments are complete, the strongest supported claim is that
the project adds useful control, observability, replay, and recovery mechanisms
and that the extracted implementation runs successfully end to end.
