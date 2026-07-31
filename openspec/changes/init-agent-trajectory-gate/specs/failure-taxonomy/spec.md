# failure-taxonomy Specification

## Purpose

Map scoring outcomes and trajectory patterns to a **single primary failure class** so operators and interviews can root-cause agent mistakes quickly.

## Requirements

### Requirement: Defined label set
The taxonomy SHALL use a fixed set of labels including at least: `OK`, `WRONG_TOOL`, `MISSING_TOOL`, `BAD_ARGS`, `ORDER_ERROR`, `HALLUCINATED_TOOL`, `INFINITE_LOOP`, `STATE_MISMATCH`, `ANSWER_LIE`, `MODEL_ERROR`.

#### Scenario: Label on every scored case
- **WHEN** a case is scored
- **THEN** the result includes a primary taxonomy label
- **AND** a short human-readable rationale

### Requirement: Deterministic classification
Classification SHALL be deterministic from scores, trajectory, and case expectations (no network required).

#### Scenario: Unit-testable
- **WHEN** the same inputs are classified twice
- **THEN** the primary label is identical

### Requirement: Priority among failures
When multiple failure signals exist, the classifier SHALL pick a primary label by documented priority (e.g. MODEL_ERROR and HALLUCINATED_TOOL before soft issues).

#### Scenario: Missing tool and weak answer
- **WHEN** required tools are missing and answer checks also fail
- **THEN** primary label is the more critical path class (e.g. `MISSING_TOOL`) unless MODEL_ERROR applies

### Requirement: OK on success
Successful cases SHALL be labeled `OK`.

#### Scenario: Clean pass
- **WHEN** aggregate verdict is PASS and no failure signals remain
- **THEN** taxonomy label is `OK`

### Requirement: Report aggregation
Suite reports SHALL include counts per taxonomy label.

#### Scenario: Summary after suite
- **WHEN** a suite run completes
- **THEN** the report shows how many cases fall into each taxonomy class present
