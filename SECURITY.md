# Security and privacy

This is a public assistant starter. It must not contain passwords, API keys, OAuth clients or tokens, bot tokens, private keys, private profile configuration, personal instructions, real conversation samples, sensitive personal records, calendar or mail data, runtime databases, or deployment logs. Even a path in `runtime.home` or a profile's name and timezone can disclose private information.

## Keep deployment inputs private

- Store credentials and real owner, account, chat or job identifiers in the runtime's supported private configuration, outside source control.
- Use placeholders in documentation and synthetic data in tests. Environment variable names such as `OPENAI_API_KEY` are references, not values.
- Keep profiles, custom instructions, runtime homes, credentials, logs, state, archives and database exports outside this checkout. The CLI rejects an instance directory inside the repository, but manually created private files still need care. `.gitignore` is a guardrail; it does not untrack a previously committed file or clean history.
- Inspect staged changes, commit messages and Git author details before publishing. Use a GitHub noreply author address when a personal email should not be public.
- Run the [file and history scans](docs/development.md) and manually review personal information. Automated secret detection cannot prove that prose is anonymous.

## If something was published

Revoke or rotate a published credential first. Removing a file from the latest commit does not invalidate the credential and does not remove older copies.

For personal information or secrets in history, prepare a sanitized history, review the resulting tree and refs, and coordinate an authorized replacement of the affected public branches/tags. Audit pull-request refs, releases, attachments and other published surfaces too. Existing clones, forks and cached commit pages can retain old content; a force push cannot recall them. Consult GitHub's [sensitive-data removal guide](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) for cache and pull-request-reference cleanup.

Do not put a secret or raw personal record in a public issue to report it. Use the repository's private vulnerability-reporting channel if enabled, or an established private maintainer channel. Share only the minimum location and impact needed to investigate.
