# trajectory-scoring Specification

## Purpose

Score recorded agent trajectories with **deterministic L1 path gates** (and feed into aggregate PASS/WARN/FAIL). This is the core AI-testing differentiator: path correctness, not only text quality.

## Requirements

### Requirement: Required tools gate
The scorer SHALL fail critically when expected required tools are missing from the trajectory.

#### Scenario: Missing create_bug
- **WHEN** expected `must_call_tools` includes `create_bug`
- **AND** the trajectory never calls `create_bug`
- **THEN** L1 reports a critical failure suitable for aggregate FAIL

### Requirement: Order constraints
The scorer SHALL enforce declared tool order constraints (e.g. create before assign).

#### Scenario: Assign before create
- **WHEN** expected order requires `create_bug` before `assign_owner`
- **AND** `assign_owner` appears first
- **THEN** L1 reports an order failure

### Requirement: Argument constraints
The scorer SHALL validate arguments against case expectations and/or schema rules (e.g. severity in allowed set, non-empty title).

#### Scenario: Invalid severity
- **WHEN** expected severity must be one of a declared set
- **AND** `create_bug` is called with an invalid severity
- **THEN** L1 reports a bad-args style failure

### Requirement: Registered tools only
The scorer SHALL flag tool names not present in the registry as hallucinated tools.

#### Scenario: Unknown tool name in trajectory
- **WHEN** a step uses tool `delete_production`
- **AND** that name is not registered
- **THEN** L1 records a hallucinated-tool failure

### Requirement: Step budget
The scorer SHALL treat exceeding max steps / forced stop without completion as a loop/budget failure when configured.

#### Scenario: Max steps hit
- **WHEN** the run ended due to max steps without a valid completion condition
- **THEN** L1 can mark an infinite-loop / budget failure

### Requirement: Aggregate verdict
The scorer SHALL map critical vs soft L1 outcomes to PASS, WARN, or FAIL per `config/scoring.yaml` (or equivalent).

#### Scenario: All critical checks pass
- **WHEN** all critical L1 rules pass and soft rules are clean
- **THEN** L1 status is PASS (subject to L2/L3 merge at suite level)

#### Scenario: Soft extra tool
- **WHEN** only a soft rule fails (e.g. unnecessary extra tool)
- **THEN** L1 may produce WARN rather than FAIL
