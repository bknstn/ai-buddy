# Optional OpenAI hosted web backend

This Hermes backend is selected as `buddy-openai` for hosted search and page
summaries. It is optional and is not enabled by a new profile. It tries the
configured Codex subscription provider first, then uses `OPENAI_API_KEY` at
`https://api.openai.com/v1` if the subscription request fails. Both routes use
the GPT-6 Sol model, medium reasoning and hosted `web_search` tool. Credentials
remain in the selected runtime's private environment.

After a subscription failure, calls use the API route during an in-process
cooldown: 60 seconds, doubling on repeated failed probes, capped at 15 minutes.
The first call after expiry probes Codex again; success resets the cooldown.
Restarting the runtime resets it. If both routes fail, the provider returns a
redacted error. A successful subscription call does not invoke the paid API.

Search returns cited sources and a model synthesis. Page reading requires a
completed `open_page` action for the exact requested URL and labels output as a
summary, not verbatim text. Hermes applies its URL safety checks. An API route
cannot guarantee access to a page.

## Optional main-agent fallback

An operator may configure the native Hermes fallback chain separately:

```yaml
fallback_providers:
  - provider: openai-api
    model: gpt-6.1-sol
    base_url: https://api.openai.com/v1
    api_mode: codex_responses
    key_env: OPENAI_API_KEY
```

`codex_responses` is Hermes's Responses API transport name; the explicit URL
and provider select the paid OpenAI API, not subscription OAuth. Native recovery
handles its own primary retries and cooldown policy. API has independent
billing and limits.

## Validation limits

The backend imports Hermes provider APIs and the OpenAI SDK. Its tests require
those runtime dependencies and do not run in this source-only environment.
Validate the plugin in an isolated target Hermes runtime. Local profile
commands only plan the source mapping; they do not configure credentials or
fallback routing.
