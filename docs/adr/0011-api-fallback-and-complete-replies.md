# ADR 0011: Add explicit API fallback and complete final delivery

Date: 2026-10-12

Status: Accepted

## Context

Subscription quota failures could block the main assistant and web research. Progressive final-text previews were also undesirable in the main chat.

## Decision

Use the native main-model fallback chain and an explicit profile-scoped OpenAI API route for hosted web. Web fallback uses exponential probe cooldown from 60 seconds to 15 minutes. Keep credentials in the private environment and final-text streaming disabled for Telegram.

## Consequences

API usage has separate billing and limits. Successful subscription calls do not invoke the API fallback. Failed routes return redacted errors. Later completed commentary in ADR 0014 does not enable final-text streaming.
