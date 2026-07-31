# trajectory-console Specification

## Purpose

Provide a professional **Trajectory Lab Console** (Streamlit) so operators can run suites, inspect tool timelines, and run secondary live probes. The UI is designed as a **lab workbench**, not a multi-turn chat product. Product principle: **the path is the product.**

## Design system (normative for MVP)

| Token | Value |
|-------|--------|
| Light background | `#F7F6F3` |
| Dark background | `#0F1419` |
| Accent | `#0D9488` |
| PASS | `#16A34A` |
| WARN | `#D97706` |
| FAIL | `#DC2626` |
| Tool step accent | `#4F46E5` |

Status chips and taxonomy badges SHALL use these colors (or clear equivalents) with readable contrast.

## Requirements

### Requirement: Lab home is Suite Run
The default/home experience SHALL be suite evaluation operations, not a multi-turn chat transcript.

#### Scenario: First open
- **WHEN** an operator opens the console default page
- **THEN** primary actions include running a suite and viewing results/KPIs
- **AND** the primary surface is not “chat with the agent” as the sole hero

### Requirement: Navigation structure
The console SHALL provide navigation to at least: Suite Run, Cases, Trajectory detail (or equivalent), Live Probe, Reports, Setup.

#### Scenario: Reach Live Probe
- **WHEN** the operator opens Live Probe from nav
- **THEN** a single-case live runner is available
- **AND** Live Probe is not required to be the default home

### Requirement: Suite Run KPIs and table
Suite Run SHALL show aggregate counts (cases, PASS, WARN, FAIL), explicit run controls (quick/full), mode indicator (fixture/live), results table, and taxonomy summary.

#### Scenario: After quick suite
- **WHEN** a quick suite completes from the console
- **THEN** KPI cards update
- **AND** a per-case table shows id, verdict, taxonomy, tool path summary, and latency when available

### Requirement: Trajectory timeline
Case detail SHALL render a **vertical tool timeline** (step order, tool name, args, result summary)—not only raw JSON.

#### Scenario: Inspect FAIL missing tool
- **WHEN** the operator opens a FAIL case with `MISSING_TOOL`
- **THEN** the timeline shows existing steps
- **AND** score card shows L1/L2/(L3) status and reasons
- **AND** expected required tools are visible for comparison

### Requirement: Score card
Detail view SHALL show verdict chip, taxonomy badge, and layer statuses (L1, L2, L3 off/skipped/score).

#### Scenario: Judge off
- **WHEN** judge is disabled
- **THEN** L3 displays as off or skipped

### Requirement: Side effects and raw JSON
Detail view SHALL show side-effect store snapshot when available and allow viewing/copying raw trajectory JSON.

#### Scenario: After create_bug
- **WHEN** trajectory includes a successful create
- **THEN** store snapshot or step result shows the created bug id

### Requirement: Live Probe (secondary)
Live Probe SHALL accept a user message (and optional presets), run the live agent when configured, show step progress, and display verdict.

#### Scenario: Missing key on Live Probe
- **WHEN** the operator runs Live Probe without an API key
- **THEN** a clear setup message is shown
- **AND** the UI links or points to Setup

### Requirement: Setup checklist
Setup SHALL surface whether API key, model, mode, max steps, and judge settings appear configured.

#### Scenario: Key absent
- **WHEN** no API key is configured
- **THEN** Setup indicates live mode is unavailable
- **AND** fixture suite remains usable

### Requirement: Theme
The console SHALL support light and dark appearance.

#### Scenario: Toggle theme
- **WHEN** the operator switches theme
- **THEN** backgrounds and chips remain legible

### Requirement: Empty and error states
The console SHALL show empty-state guidance before any run and clear errors on provider/rate-limit failures.

#### Scenario: No runs yet
- **WHEN** no suite has been run in the session
- **THEN** empty state invites “Run quick suite”

### Requirement: Explicit run actions
Suite and Live Probe execution SHALL require an explicit user action (button), not implicit re-run on unrelated widget changes.

#### Scenario: Change filter only
- **WHEN** the operator changes a table filter without pressing Run
- **THEN** a new SUT suite is not automatically executed
