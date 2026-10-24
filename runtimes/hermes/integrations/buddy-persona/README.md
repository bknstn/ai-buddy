# Optional assistant instruction fragments

This Hermes-specific bundle offers optional, editable instructions for assistant role, communication, live progress and reports. It does not supply a persona, user profile, channel, language, schedule or domain configuration. Shared runtime-neutral starting instructions live in [`core/instructions`](../../../../core/instructions/).

Review each file and copy only the fragments that fit the private instance into its runtime instructions. The local profile plan lists manual mappings; it does not compose prompts or modify `SOUL.md`. Adapt the fragments to the name, language and preferences chosen in the private profile. Keep personal facts and preferences out of this repository.

- [`role.md`](role.md): general role and permission boundaries.
- [`communication.md`](communication.md): adaptable language and style guidance.
- [`live-progress.md`](live-progress.md): optional updates during substantial user-requested work. It refers to the `buddy_progress` tool only when the companion plugin is installed and available.
- [`scheduled-reports.md`](scheduled-reports.md): guidance for a report the user requests or separately authorizes. It does not establish a schedule or delivery destination.

These files are source material, not a ready-made operating profile. Every integration remains disabled unless an operator configures it separately.
