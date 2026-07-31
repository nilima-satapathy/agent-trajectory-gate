# free-tier-meter Specification

## Purpose

Make free cloud credit usage **visible** during live agent and judge calls so demos stay intentional and do not silently exhaust quotas.

## Requirements

### Requirement: Track live usage
The system SHALL track approximate request and/or token usage for live agent loop calls in the current session (and judge calls when enabled).

#### Scenario: After live probe
- **WHEN** a Live Probe run completes with network calls
- **THEN** the meter shows increased usage versus session start

### Requirement: Console visibility
When live mode is active, the Trajectory Console SHALL display a free-tier meter or usage summary.

#### Scenario: Suite Run in live mode
- **WHEN** the operator selects live mode in the console
- **THEN** a free-tier usage indicator is visible in the chrome/sidebar

### Requirement: Configurable budget
Daily or session budget defaults SHALL be configurable (env or settings) for demo purposes.

#### Scenario: Budget near limit
- **WHEN** usage approaches the configured budget
- **THEN** the UI indicates high usage (warning state)

### Requirement: Fixture mode does not burn credits
Fixture runs SHALL not increment LLM usage counters.

#### Scenario: Fixture suite
- **WHEN** a fixture suite completes
- **THEN** the meter does not attribute LLM tokens to those cases
