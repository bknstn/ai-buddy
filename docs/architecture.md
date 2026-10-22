# Architecture

Buddy combines a conversational control plane with small, independently testable integrations. It keeps domain logic in separate repositories and private state in the runtime home.

## Responsibilities

| Layer | Owns | Contract |
| --- | --- | --- |
| Telegram | User input and message delivery | Hermes platform adapter |
| Hermes Agent | Sessions, tools, memory, provider routing and scheduling | Upstream runtime and plugin interfaces |
| Buddy integrations | Session/progress policies, review collection, continuity and delivery gates | Plugin hooks, scripts and prompt fragments |
| Domain engines | Product discovery, recovery/training and learning workflows | Stable CLI commands with JSON or Markdown output |
| External services | Authorized calendar, tasks, mail, transcription and search | Separately configured credentials and scopes |
| Private runtime storage | Conversations, context ledger, queues, control state and secrets | Local files/databases excluded from source control |

The named domain workspaces are Idea Maze, Health OS and Learning OS. Their source, data and deployment are separate concerns. This repository supplies integration contracts and design context, not those engines' implementations.

## Request flow

Hermes authorizes an incoming Telegram request before opening the relevant session and executing tools. The session-policy plugin can create a new daily conversation after an eligible greeting, provided active work is protected. The assistant calls domain CLIs with an explicit working directory and interprets their actual output.

During substantial user-requested work, completed assistant commentary explains meaningful progress. The live-progress plugin tracks the current declared stage and can emit a bounded waiting notice. It does not expose tool arguments or hidden reasoning, and it does not infer progress from elapsed time.

The native Telegram adapter receives the complete final reply and handles splitting. Concision is a communication preference, not a hard character limit.

## Background review flow

Heartbeat separates preparation from delivery:

1. A bounded collector reads explicitly authorized sources and a small fragment of the configured main conversation.
2. Private daily and weekly reviews assess usefulness and produce proposals.
3. A deterministic gate validates freshness, quiet hours, deduplication, snoozes and the notification budget.
4. Delivery emits only the useful message, or remains silent.

The context ledger stores source-backed decisions, commitments, waiting items, preferences and feedback. Provenance checks verify that a quotation exists; they do not prove the model interpreted it correctly. Saved context does not authorize external actions. New human input or a changed ledger invalidates stale prepared advice.

## Boundaries and limitations

- Persona instructions guide behavior. Code enforces delivery limits and scope checks.
- A separate assistant instance has its own runtime, configuration, provider session and state. Sharing a Linux user provides operational separation, not a filesystem security boundary.
- Session and progress plugins wrap private Hermes gateway interfaces. Validate compatibility before upgrading; no upstream source patch is required.
- Background reviews consume model calls even when delivery stays silent. They cannot monitor a stopped gateway independently.
- Source failures mean unknown. Neither a successful collector nor a saved delivery reservation proves that a message reached the user.
- Credentials, personal profiles and raw domain data are deployment inputs. Public examples use placeholders or synthetic fixtures.

The reasoning and historical adoption dates are recorded in [ADRs](adr/README.md).
