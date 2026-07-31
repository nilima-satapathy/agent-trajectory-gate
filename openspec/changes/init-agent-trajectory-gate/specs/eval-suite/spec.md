# eval-suite Specification

## Purpose

Define **golden cases**, suite selection (quick/full), and a **batch runner** that invokes the SUT, scores results, attaches taxonomy, and writes reports.

## Requirements

### Requirement: Case schema
Each golden case SHALL include at least: `id`, `input`, and `expected` constraints for tools/order/args/answer as needed for scoring.

#### Scenario: Load cases
- **WHEN** the suite loader reads the golden dataset
- **THEN** cases validate against the documented schema
- **AND** invalid cases are rejected or skipped with a clear error

### Requirement: Suite sizes
The project SHALL ship a `quick` suite of at least 8 cases and a `full` suite of at least 25 cases.

#### Scenario: Quick suite
- **WHEN** the operator runs `--suite quick`
- **THEN** only cases marked for quick (or the quick subset) execute

### Requirement: Case mix
The full suite SHALL include multiple categories: happy path, list-only (no create), order traps, adversarial, multi-step, and edge cases.

#### Scenario: List-only expectation
- **WHEN** a list-only case is scored
- **THEN** expectations forbid `create_bug` (or equivalent) as required by the case

### Requirement: Batch runner
A CLI runner SHALL execute a suite in `fixture` or `live` mode and write `reports/last_run.json` plus a human-readable summary.

#### Scenario: Fixture quick run
- **WHEN** `python evals/run_suite.py --suite quick --mode fixture` is executed
- **THEN** a report file is written with per-case verdict and taxonomy
- **AND** no API key is required

### Requirement: Exit code for CI
The runner SHALL support a non-zero exit code when any case FAILs (for CI gating).

#### Scenario: Failures fail the process
- **WHEN** at least one case is FAIL and fail-on-error is enabled
- **THEN** the process exit code is non-zero
