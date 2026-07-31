# agent-sut Specification

## Purpose

Run a **live multi-step tool-calling agent** against an OpenAI-compatible LLM (default free-tier Groq). The agent plans, calls **registry** tools, and produces a final answer plus a recorded **trajectory**.

## Requirements

### Requirement: Live tool-calling loop
The live agent SUT SHALL call the configured LLM with tool schemas and execute returned tool calls via the registry until a final text response or max steps.

#### Scenario: Multi-step create and assign
- **WHEN** the user input requires creating a bug and assigning an owner
- **AND** live mode is enabled with a valid API key
- **THEN** the agent may issue one or more tool calls
- **AND** each tool call is executed through the registry
- **AND** a final natural-language answer is produced
- **AND** a trajectory log of steps is returned

### Requirement: Trajectory recording
Every live run SHALL record ordered steps including tool name, arguments, and tool results (and model-only final step).

#### Scenario: Trajectory fields present
- **WHEN** a live run completes
- **THEN** each tool step includes at least `step`, `tool`, `args`, and `result`
- **AND** the final answer string is available separately or as a terminal step

### Requirement: Max steps budget
The agent loop SHALL stop when `MAX_TOOL_STEPS` is reached if no final answer was produced.

#### Scenario: Budget exhausted
- **WHEN** the model continues requesting tools beyond the configured max steps
- **THEN** the run stops
- **AND** the result is scorable as a loop/budget failure

### Requirement: OpenAI-compatible configuration
The live client SHALL use `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `OPENAI_MODEL` (or documented equivalents).

#### Scenario: Groq free tier
- **WHEN** base URL points to Groq’s OpenAI-compatible endpoint and a valid key is set
- **THEN** the agent can complete at least one tool-calling smoke case
- **AND** documentation names Groq as the default free provider

### Requirement: Missing key and rate limit handling
The live SUT SHALL fail clearly when the API key is missing or the provider returns rate-limit errors.

#### Scenario: No API key
- **WHEN** live mode is requested without an API key
- **THEN** the system returns a clear configuration error
- **AND** does not hang indefinitely

#### Scenario: HTTP 429
- **WHEN** the provider rate-limits the request
- **THEN** the error is surfaced to the caller/console
- **AND** the process does not crash without a message

### Requirement: Persist live runs
Live runs SHOULD be saved under `reports/live_runs/` for offline re-scoring and demos.

#### Scenario: Save after live case
- **WHEN** a live case completes successfully enough to produce a trajectory
- **THEN** a JSON artifact is written that includes case id (if any), trajectory, and final answer
