# fixture-sut Specification

## Purpose

Provide an **offline deterministic SUT** that returns pre-authored trajectories and answers so CI, demos, and scoring logic run without API keys or network.

## Requirements

### Requirement: Offline execution
The fixture SUT SHALL run without calling external LLM APIs.

#### Scenario: No network dependency
- **WHEN** `SUT_MODE=fixture` (or equivalent) and a golden case with fixture data is run
- **THEN** the SUT returns trajectory + final answer without requiring `OPENAI_API_KEY`

### Requirement: Case-bound fixtures
Fixture outputs SHALL be bound to case identifiers or embedded fixture trajectories on the case.

#### Scenario: Known case id
- **WHEN** case `triage-001` has a fixture trajectory
- **THEN** running the fixture SUT for that case returns the expected tool sequence and answer

### Requirement: Deliberate failure fixtures
The fixture set SHALL include at least one trajectory intended to FAIL scoring (for taxonomy and UI demos).

#### Scenario: Missing tool fixture
- **WHEN** a fixture omits a required tool call
- **THEN** L1 scoring can produce FAIL with `MISSING_TOOL` (or equivalent)

### Requirement: Same result shape as live
Fixture results SHALL use the same trajectory/answer structure as the live agent SUT so scorers are shared.

#### Scenario: Shared scorer
- **WHEN** the suite runner scores a fixture result
- **THEN** it uses the same L1/L2 scoring entrypoints as for live results
