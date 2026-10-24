# Shared core

This directory contains generic instruction fragments that a runtime module can include in its local plan. They do not prescribe a name, timezone, communication channel, model provider, schedule or domain track.

An operator can add instance-specific guidance to the private profile under `instructions/`. Do not put personal preferences, private facts or installation credentials into these shared files. A runtime module must document how it uses these fragments; the presence of a file here does not make an upstream runtime load it automatically.

The starter plan lists the Markdown files in `instructions/` as mappings for manual review. It does not install them or load them into a running assistant.
