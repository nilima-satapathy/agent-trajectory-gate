# regression-ci Specification

## Purpose

Keep **offline quality gates** green in CI without free-tier spend, while allowing optional live tests locally.

## Requirements

### Requirement: Offline pytest default
Default automated tests SHALL pass without network or API keys.

#### Scenario: CI pytest
- **WHEN** `pytest -m "not live"` (or equivalent) runs in CI
- **THEN** unit and fixture integration tests execute
- **AND** live-marked tests are excluded

### Requirement: Live marker
Live tests SHALL be marked (e.g. `@pytest.mark.live`) and skip when no key is present.

#### Scenario: Live without key
- **WHEN** live tests are collected without `OPENAI_API_KEY`
- **THEN** they skip rather than fail the suite

### Requirement: GitHub Actions workflow
The repo SHALL include a GitHub Actions workflow that installs dependencies and runs offline tests and/or fixture quick suite.

#### Scenario: PR push
- **WHEN** code is pushed to the default branch or a PR
- **THEN** the workflow runs offline quality checks
- **AND** does not require secrets for the default job

### Requirement: Fixture suite in CI
CI SHALL run a fixture quick suite (pytest or `evals/run_suite.py --mode fixture`) and fail on FAIL verdicts when configured.

#### Scenario: Fixture gate
- **WHEN** the fixture quick suite produces a FAIL case under fail-on-error
- **THEN** the CI job fails

### Requirement: Documentation
README SHALL document offline CI commands and how to run live smoke locally with Groq.

#### Scenario: Contributor reads README
- **WHEN** a contributor follows Quick start
- **THEN** they can run offline gates without creating an API key
