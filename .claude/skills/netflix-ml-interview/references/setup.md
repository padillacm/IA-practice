# Setup of a new session

Read `netflix-ml-interview/catalog.yaml` for validation and for the summary (the catalog is the only content file the orchestrator reads; never open `netflix-ml-interview/stages/**`).

## 1. Environment

1. Detect the python command (`python --version`, `python3 --version`, `py --version`); call it `PY`.
2. `PY netflix-ml-interview/scripts/sim.py info`. If it reports `CLAUDE_CODE_REMOTE='true'`, remember the ephemeral warning for the summary.
3. `PY netflix-ml-interview/scripts/sim.py guard`. Exit 0: continue. Exit 1: print what it says (the `.gitignore` entry for `netflix-ml-interview/sessions/` is missing or session files are tracked) and stop; do not create anything. Exit 3: report the error and stop. This check precedes any write.

## 2. Arguments

Accepted `key=value` pairs (also free text such as "Applied Scientist, L6, in Spanish"):

| Key | Values | Default |
|---|---|---|
| `role` | `mle`, `rs`, `ds` | asked |
| `level` | `L4`, `L5`, `L6` | `L5` |
| `lang` | `en`, `es` | `en` |
| `stages` | `full`, `screen`, `vo1`, `vo2`, a stage id, `stage@variant`, comma separated | `full` |
| `domain` | catalog `domains` | the role's `default_domain` |
| `feedback` | `immediate`, `deferred` | `immediate` |
| `time_scale` | positive number | `1.5` |
| `background` | path to a CV / projects file | none |

Title equivalence: ML Engineer, MLE -> `mle`. Research Scientist, ML Scientist, Applied Scientist -> `rs`. Data Scientist -> `ds` ("experimentation and analytics" track). Always tell the candidate which role you picked; for Applied Scientist also explain that `ds` is the experimentation and analytics track.

A stage without `@variant` uses the role's variant (`variant_by_role`). If the role has none for that stage, use the stage's single or default variant. Optional stages outside the loop (for example `ai-assisted-coding`) use `default_phase`.

## 3. Asking for what is missing

Use AskUserQuestion with proposed defaults, one short question per missing value (role first, then stages, then optional ones such as domain, level, feedback). Ask in English unless `lang=es` was passed. If the candidate gives `background`, `Read` the file; extract a short candidate profile (roles, projects, domains, tools; no invented facts) to be stored with `sim.py set <session> candidate_profile=@<file>` after the session exists (write the profile to a scratchpad file first, not under `sessions/`). Without a background the profile is built later from `hm-screen`; if the candidate does only `project-deep-dive`, the interviewer will ask them to summarize their project first.

## 4. Validation

Compare every value with the catalog. Reject, list the valid options, and do not start when:
- role, level, lang, domain or feedback is not in its list;
- a stage id does not exist (`stages=foo`);
- a variant does not exist or is incompatible with the role (`coding@foo`);
- `time_scale` is not a positive number;
- the background path does not exist.

`sim.py new` validates again (exit 2 with `Valid: ...`); relay that message as a rejection.

## 5. Summary

Show, in the session language:
- role (and title equivalence), level, language, domain, feedback mode, time_scale;
- the instances in order, grouped by phase (screen / VO1 / VO2), each as `NN-stage@variant (minutes)`; mark optional additions;
- whether the cut after VO1 is on (role `cut: yes`, and the selection includes both VO1 and VO2) or off;
- background: provided or built from `hm-screen`;
- variability warning: the real Netflix loop varies by team and level; this is an approximation, confirm the structure with your recruiter;
- ephemeral warning if `CLAUDE_CODE_REMOTE=true`: local history is lost when the container recycles;
- cost note for full loops: one phase per conversation, then `resume`;
- how to use `::time`, `::pause`, `::end`, `::help` (and `::ai`, `::apply` in ai-assisted-coding).

## 6. Confirmation and creation

Ask for explicit confirmation (AskUserQuestion: start / change something / cancel). No stage starts before a yes.

Then:

```
PY netflix-ml-interview/scripts/sim.py new --role <r> --level <l> --lang <lang> --domain <d> --stages <list> --feedback <f> --time-scale <x> [--order given] [--background <path>] [--python <PY>]
```

`new` runs the guard itself, creates the session directory and the ordered instances, and prints the session id and path. Keep the session id; use `latest` or the id in later calls. Note any `warnings` it prints. Then load the tools (`ToolSearch` query `select:SendMessage,AskUserQuestion`), read `references/relay-protocol.md`, and start the first instance.

If the selection is a single stage, no debrief is convened (the scorecard is the result).
