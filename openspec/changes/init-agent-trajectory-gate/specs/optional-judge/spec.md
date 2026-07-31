# optional-judge Specification

## Purpose

Provide an **optional L3 LLM-as-judge** layer for subjective quality (e.g. bug description usefulness), using free-tier credits only when enabled. Default is **off**.

## Requirements

### Requirement: Disabled by default
The judge SHALL be disabled unless explicitly enabled via config/env (`JUDGE_ENABLED=true` or console toggle).

#### Scenario: Default run
- **WHEN** a suite runs with default settings
- **THEN** no judge API call is made
- **AND** aggregate verdict depends only on L1/L2

### Requirement: Rubric-based score
When enabled, the judge SHALL score the final answer (and optional trajectory summary) against a documented rubric and return pass/fail or numeric score with reasons.

#### Scenario: Judge enabled
- **WHEN** judge is enabled and a valid API key is present
- **THEN** the result includes L3 score/status and reasons
- **AND** L3 participates in aggregate verdict per scoring config

### Requirement: Skip cleanly without key
When judge is enabled but no API key is available, the system SHALL skip L3 with an explicit status rather than crashing.

#### Scenario: Judge on, no key
- **WHEN** `JUDGE_ENABLED=true` and API key is missing
- **THEN** L3 is marked skipped/unavailable
- **AND** the suite continues

### Requirement: Meter integration
Judge calls SHALL count toward the free-tier meter when metering is active.

#### Scenario: Judge consumes budget
- **WHEN** a judge call succeeds
- **THEN** the free-tier meter reflects additional usage
