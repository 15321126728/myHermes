# Ablation study protocol

## Research question

This study measures the marginal and standalone effects of seven guided-agent
mechanisms while holding the agent class, parser, model, task image, prompt
template, temperature, base episode budget, and retry policy constant.

| Code | Mechanism |
| --- | --- |
| C | Five-category cognitive-error detection |
| D | Seven-layer runtime diagnosis |
| T | Ternary process feedback |
| A | Adaptive episode extension |
| E | Runtime artifact verification |
| K | Knowledge-document hints |
| U | Pre-action comprehension check |

## Primary matrix

The primary study contains Base, Full, and seven leave-one-out profiles:

| Profile | Disabled mechanisms |
| --- | --- |
| `base` | C, D, T, A, E, K, U |
| `full` | None |
| `full-minus-cognitive-detection` | C |
| `full-minus-layer-diagnosis` | D |
| `full-minus-ternary-feedback` | T |
| `full-minus-adaptive-episodes` | A |
| `full-minus-runtime-verification` | E |
| `full-minus-knowledge-hints` | K |
| `full-minus-comprehension-check` | U |

Optional `base-plus-*` profiles are available for standalone-effect analysis.
All profiles run through `GuidedInterventionAgent`; Base does not substitute a
different class, so implementation differences outside the seven flags remain
controlled.

## Pilot

The versioned pilot list contains 20 tasks in
`experiments/pilot-tasks.txt`. The default three replicate IDs and nine primary
profiles produce 540 paired trials.

```bash
uv run hermes-ablation \
  --dataset-path /path/to/terminal-bench/original-tasks \
  --task-file experiments/pilot-tasks.txt \
  --experiment-id ablation-pilot-v2
```

The runner performs a minimal chat-completion preflight, selects a working API
key environment variable without serializing the key, cleans up trial
containers, writes a manifest before execution, and resumes completed valid
trials. Infrastructure failures such as `unknown_agent_error` are not treated
as experimental observations.

## Metrics

The trial CSV records success, failure mode, token counts, wall time, episodes,
effective budget, extension count, cognitive detections, diagnosis layers,
ternary-state counts, completion rejections, knowledge hints, comprehension
failures, and trajectory resets. The summary JSON reports aggregate accuracy,
mean cost, mechanism-event totals, and paired Full-versus-profile outcomes.

Primary outcome: task success. Secondary outcomes: input/output tokens, wall
time, episode count, and cost per successful task. Adaptive episodes must also
be compared against fixed low-budget and fixed high-budget controls before its
benefit is attributed to policy quality rather than additional compute.

## Smoke evidence

The completed `ablation-smoke-v3` run used `hello-world`, replicate ID 0, and a
five-episode cap:

| Profile | Success | Episodes | Input tokens | Output tokens | Wall time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base | 1 | 2 | 747 | 145 | 31.21 s |
| Full | 1 | 5 | 3477 | 473 | 29.51 s |

This smoke validates execution and aggregation, not effectiveness. It exposed
and led to fixes for credential-selection ambiguity, comprehension/parser
format conflict, invalid history compaction, and missing positive feedback when
runtime artifact verification succeeds. A later Full-only run confirmed that
history compaction no longer creates parser warnings.

## Analysis

Use task/replicate paired comparisons. Report absolute accuracy deltas, paired
win/loss counts, bootstrap 95% confidence intervals, and McNemar tests with Holm
correction across the seven leave-one-out comparisons. Knowledge effects must
be reported separately for tasks with a verified knowledge document; tasks
without one are negative controls where K must remain a no-op.
