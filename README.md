# AI Buddy

AI Buddy is a general-purpose AI assistant for everyday tasks. Give it requests in conversation, customize how it works, and connect the tools and services it needs.

## What you can do

- Manage your calendar: check availability, create events, and reschedule meetings.
- Carry out requests in connected services.
- Find information and prepare summaries.
- Tailor the assistant's instructions and communication style to your needs.

Capabilities depend on the tools, integrations, and permissions you configure. The repository provides assistant instructions, profile tools, and optional integrations. Hermes is the only runtime adapter currently included.

## Get started

Requires **Python 3.11+** for the local profile CLI.

```bash
git clone https://github.com/bknstn/ai-buddy.git
cd ai-buddy
python3 -m buddy init --path /path/to/private/assistant-profile
python3 -m buddy check --profile /path/to/private/assistant-profile
python3 -m buddy plan --profile /path/to/private/assistant-profile --format text
```

Choose a private profile path outside the checkout whose parent directory already exists. Edit its `config.toml` to set the assistant's name, timezone, and optional features; add personal instructions under `instructions/`.

Install [Hermes Agent](https://github.com/NousResearch/hermes-agent) separately, then follow the [Hermes runtime guide](runtimes/hermes/README.md) to review and apply the configuration and set up integrations. The profile commands only create, validate, and preview configuration; runtime setup is manual.

Keep personal profiles, credentials, and assistant data outside the repository.

## Documentation

- [Hermes setup and integrations](runtimes/hermes/README.md)
- [Architecture and runtime adapters](docs/architecture.md)
- [Profile CLI and development](docs/development.md)
- [Operations](docs/operations.md)
- [Security and privacy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)

## License

[MIT](LICENSE). Separately installed runtimes and services have their own licenses and terms.
