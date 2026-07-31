# tool-registry Specification

## Purpose

Provide an **author-defined** set of tools (Python functions + OpenAI-compatible schemas + side-effect store) that the agent may call. Tools are never created by the LLM at runtime in MVP.

## Requirements

### Requirement: Author-defined tool set
The system SHALL expose a fixed registry of tools implemented in application code.

#### Scenario: Registry lists MVP tools
- **WHEN** the registry is initialized
- **THEN** it includes at least `search_known_issues`, `create_bug`, `assign_owner`, `lookup_user`, and `list_open_bugs`
- **AND** each tool has a name, description, and parameter schema

### Requirement: Schema export for LLM tool calling
The registry SHALL export tool definitions in OpenAI-compatible tools/function format.

#### Scenario: Schemas ready for chat completions
- **WHEN** the agent SUT requests tool schemas
- **THEN** the registry returns a list suitable for the Chat Completions `tools` parameter
- **AND** parameter types and required fields are present

### Requirement: Execute with structured results
The registry SHALL execute a tool by name and arguments and return a structured result (success payload or error).

#### Scenario: Create bug side effect
- **WHEN** `create_bug` is executed with valid title, severity, and description
- **THEN** a new bug is stored with a generated `bug_id`
- **AND** the result includes that `bug_id`

#### Scenario: Unknown tool
- **WHEN** execution is requested for a name not in the registry
- **THEN** the call fails in a controlled way (error result or exception mapped by the agent loop)
- **AND** no side effect is applied

### Requirement: Observable store
The system SHALL allow inspection of side-effect state after tool execution (e.g. bugs created, assignments).

#### Scenario: Inspect after assign
- **WHEN** `create_bug` then `assign_owner` succeed
- **THEN** the store shows the bug with the assigned team

### Requirement: No model-defined tools in MVP
The MVP SHALL NOT accept tools defined solely by model-generated code or ad-hoc model output.

#### Scenario: Only registry tools are callable
- **WHEN** the agent attempts a tool name outside the registry
- **THEN** scoring may classify `HALLUCINATED_TOOL`
- **AND** the registry does not dynamically register that tool
