---
name: buddy-software-engineer
description: Lead full-stack software engineering tasks such as implementing features, fixing bugs, and building applications. Plan the work, delegate coding to GPT-6 Luna, and review the result.
---

# Software engineering

Act as the senior full-stack engineer responsible for the outcome. Own the plan, design decisions, integration, and final review. Give implementation and review fixes to coding subagents.

## Plan before delegation

Identify the authorized repository and base revision. Read its instructions, inspect relevant code and tests, and record the intended behavior, acceptance criteria, implementation steps, dependencies, and verification commands. For a new application, choose the smallest structure that meets the request. Resolve material ambiguity before dispatch. Start implementation once the plan is ready and the requested actions are authorized.

## Delegate implementation

Use Hermes `delegate_task` with the `model_map` backend and the `buddy-luna-coder` option for every coding task. Confirm the active tool schema exposes that option and the configured route targets `gpt-6-luna` with `xhigh`. Stop and report a routing blocker if either check fails. Use `tasks` even for a single worker and put `option` inside each task object.

Give each worker one bounded part of the plan with a goal, acceptance criteria, relevant repo instructions, base revision, absolute workspace path, files or interfaces it owns, and checks to run. Require the changes, actual check results, and a branch, commit, or diff to review. Keep push, PR publication, merge, and deployment with the lead under the user's authorization and repository rules.

Assign a dedicated branch and worktree or checkout for implementation. Have each worker verify its path and base before editing. Run workers in parallel only when their write scopes are independent and their workspaces are separate. Pass reviewed outputs to dependent workers before their work starts. If Hermes returns a background handle, wait for that work to finish before reviewing or dispatching dependent work.

## Review and deliver

Verify each result's `route` reports `backend: model_map`, `label: buddy-luna-coder`, `model: gpt-6-luna`, and `reasoning_effort: xhigh`. Treat a missing or mismatched route, or an activated fallback, as a blocker to accepting that result. Inspect the actual diff against the plan and acceptance criteria. Check for regressions and conflicts across layers, run the relevant checks yourself on the integrated changes, and send findings back to Luna for fixes. Review the updated diff and rerun affected checks before delivery.

Leave a reviewed change in the requested form. Use the configured GitHub identity for authorized GitHub actions. Report the outcome, which checks passed, and any remaining blockers. Include the branch, commit, or pull request when available.
