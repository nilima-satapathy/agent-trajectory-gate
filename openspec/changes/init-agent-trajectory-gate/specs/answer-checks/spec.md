# answer-checks Specification

## Purpose

Apply **L2 final-answer checks** so the agent cannot “talk past” failed or missing tool actions. Complements L1 path scoring.

## Requirements

### Requirement: Must-include phrases
The answer checker SHALL enforce case-level `answer_must_include` constraints when present.

#### Scenario: Bug id in answer
- **WHEN** the trajectory created `BUG-1042` and expected answer must include that id (or a pattern)
- **AND** the final answer omits it
- **THEN** L2 reports a failure or warn per configuration

### Requirement: Answer lie detection
The checker SHALL detect claims of successful actions that did not occur in the trajectory.

#### Scenario: Claims create without tool
- **WHEN** the final answer claims a bug was created
- **AND** `create_bug` was never called
- **THEN** L2 reports a hard failure suitable for `ANSWER_LIE`

### Requirement: Forbidden phrases
The checker SHALL fail or warn when configured forbidden phrases appear in the final answer.

#### Scenario: Unsafe claim
- **WHEN** the answer contains a configured forbidden phrase
- **THEN** L2 records a policy-style failure

### Requirement: Merge with L1
L2 outcomes SHALL merge with L1 into the aggregate verdict (FAIL overrides PASS; WARN does not clear FAIL).

#### Scenario: L1 pass L2 fail
- **WHEN** L1 is PASS and L2 is critical FAIL
- **THEN** aggregate verdict is FAIL
