# Domain adapter example

This folder shows a small, synthetic request/response envelope for an optional domain adapter. It documents a possible boundary between an assistant runtime and an independently maintained engine; it is not a production protocol, installed integration or business engine.

The adapter author chooses the real command, authentication method, workspace rules, supported operations, validation and failure behavior. Keep domain logic, persistent data, tests and release lifecycle in the engine's own project. Pass explicit workspace and operation scope, validate untrusted input and output, and return structured results with clear errors. Avoid putting sensitive domain records into prompts or logs.

The fixtures use placeholder paths and invented values. They are examples only; the profile CLI does not register or enable this adapter.

## Example envelope

Request:

```json
{
  "schema_version": 1,
  "operation": "lookup",
  "workspace": "/path/to/synthetic/workspace",
  "input": {
    "query": "sample item"
  }
}
```

Response:

```json
{
  "schema_version": 1,
  "ok": true,
  "result": {
    "summary": "One synthetic entry matched.",
    "items": [
      {
        "id": "sample-001",
        "label": "Synthetic example"
      }
    ]
  },
  "warnings": []
}
```

Define a separate error shape and document exit codes, timeouts, output size limits, retries and side effects before using an adapter. A successful process exit does not prove that a result is current or correct. This example does not define those semantics for any particular engine.
