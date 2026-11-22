# Audigest for Hermes

`buddy-audigest` adds the `audigest` tool for local attachments and saved transcripts. The tool uses the separate [Audigest CLI](https://github.com/bknstn/audigest). It supports transcript-first ingestion, speech-to-text, transcript readback, summaries, and English notes. For this integration, use an attachment from the active profile or place an operator-approved file in its private Audigest inbox. Run Audigest separately for URL ingestion and applying transcripts to project files.

## Install

Use Hermes with the scoped plugin API (`register_tool` and `agent.secret_scope.get_secret`), Python 3.12+, and `uv`. Verify on the target Hermes release. Set `HERMES_HOME` to the intended profile and `AUDIGEST_CHECKOUT` to a separately cloned, reviewed Audigest revision. Run from the AI Buddy checkout:

```sh
umask 077
install -d -m 700 "$HERMES_HOME/audigest" "$HERMES_HOME/audigest/inbox" \
  "$HERMES_HOME/plugins/buddy-audigest"
if [ ! -e "$HERMES_HOME/audigest/config.toml" ]; then
  printf 'provider = "auto"\n' > "$HERMES_HOME/audigest/config.toml"
fi
UV_PROJECT_ENVIRONMENT="$HERMES_HOME/audigest/venv" \
  uv sync --project "$AUDIGEST_CHECKOUT" --python 3.12 --frozen --no-dev --extra openai
install -m 644 runtimes/hermes/integrations/buddy-audigest/__init__.py \
  runtimes/hermes/integrations/buddy-audigest/plugin.yaml \
  "$HERMES_HOME/plugins/buddy-audigest/"
HERMES_HOME="$HERMES_HOME" hermes plugins enable buddy-audigest
```

Enable the `audigest` toolset for the intended channels if the profile uses a toolset allowlist. Reload the intended Hermes gateway and verify the tool appears for its enabled channels. For the optional profile planner mapping, add `buddy-audigest` to the existing private profile's `features.enabled` list.

The plugin uses the active profile's `OPENAI_API_KEY` through Hermes's secret store for calls with `use_openai: true`. Keep the credential in that store. Selecting OpenAI can upload the audio or transcript text and incur charges. Ingest tries local text and captions first. With `use_openai` omitted, ingestion uses existing text or a cached transcript, and the processors use their caches. To override Audigest's default processor model, set `plugins.entries.buddy-audigest.settings.processor_model` in the Hermes profile.

## Smoke test

Place a short synthetic `.txt` file in the inbox and call `ingest` with its absolute path. Reuse the returned transcript ID with `show`. If API processing is authorized, call `summarize` with the same ID and `use_openai: true`, then call it again with `use_openai: false` to check cache reuse. For speech-to-text, use a short synthetic audio file with `transcribe` and explicitly select OpenAI. Remove test files and test cache entries after validation.

Cache files stay in `$HERMES_HOME/audigest/cache`. Ingestion and transcription return the saved transcript ID. `show`, `summarize`, and `english` return their structured results when they fit in the tool response. Larger artifacts remain available in the profile cache.
