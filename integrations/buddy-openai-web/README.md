# Buddy OpenAI web backend

Profile-local Hermes backend selected as `buddy-openai` for search and extract.
Uses Buddy Codex OAuth first, then the existing profile-scoped `OPENAI_API_KEY`
at `https://api.openai.com/v1` when the subscription request fails. Both routes
use GPT-6 Sol, medium reasoning, and the hosted `web_search` tool. No Tavily fallback.
The key stays in Buddy's private environment; no credential is embedded in source.

After a subscription failure, web calls use API during an in-process cooldown:
60 seconds, doubling on repeated failed probes, capped at 15 minutes. The first
call after expiry probes Codex; success resets the cooldown. Restart resets it.
The SDK permits one retry per route. If both routes fail, return a redacted error.
A successful subscription call never invokes the paid API route.

Search returns cited sources plus a model synthesis. Page reading requires a
completed `open_page` action for the exact requested URL and labels output as
a model summary, not verbatim text. Hermes applies its normal URL safety checks.
Inaccessible pages are reported honestly; an API route cannot guarantee access.

## Main-agent fallback

Buddy's private config uses the native runtime chain:

```yaml
fallback_providers:
  - provider: openai-api
    model: gpt-6.1-sol
    base_url: https://api.openai.com/v1
    api_mode: codex_responses
    key_env: OPENAI_API_KEY
```

`codex_responses` is Hermes's Responses API transport name; the explicit URL and
provider select paid OpenAI API, not subscription OAuth. Main reasoning remains
medium. Native recovery handles quota/rate limits, auth failures and exhausted
transient retries, with its own primary retry/cooldown policy. API has independent
billing and limits; a failed API route remains a terminal error.

TAVILY_API_KEY remains for the independent Idea Maze pipeline.

## Validation and deployment

Run with Buddy runtime Python, PYTHONPATH and HERMES_HOME:

    python /path/to/test_backend.py
    python -m hermes_cli.main plugins validate /path/to/buddy-openai-web

Publish reviewed source to GitHub main before fast-forwarding the VPS deployment
checkout. Install this directory into Buddy's plugins directory, add the private
fallback config, and quietly restart only Buddy after active turns have drained.
Rollback uses the prior published plugin source and removes the new fallback
entry; no historical private-config backup is assumed to exist.
