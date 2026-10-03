"""Buddy-only collectors, private proposal queue and deterministic delivery gate.

Hermes cron supplies the reasoning and Telegram transport. No secrets or personal
data are written into the source repository. Stdout from deliver is the message.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import socket
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Warsaw")
HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes-buddy"))
STATE = HOME / "plugin-data/buddy-heartbeat"
TOPICS = {"calendar", "health", "nutrition", "learning", "projects", "buddy"}
socket.setdefaulttimeout(20)


def now():
    return datetime.now(TZ)


def read(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w") as stream:
            os.chmod(tmp, 0o600)
            json.dump(value, stream, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


@contextlib.contextmanager
def locked():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / ".lock").open("a") as stream:
        os.chmod(STATE / ".lock", 0o600)
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def run(args, cwd=None, timeout=30):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                            timeout=timeout, check=True)
    return result.stdout.strip()


def source(function):
    # API exception messages can contain private URLs, request payloads or tokens.
    try:
        return {"status": "ok", "data": function()}
    except Exception as error:
        return {"status": "unavailable", "error_type": type(error).__name__}


def controls():
    return read(STATE / "controls.json", {"paused": False, "snoozes": {}})


def suppressed(settings, instant):
    if settings.get("paused"):
        return True
    until = settings.get("pause_until")
    return bool(until and datetime.fromisoformat(until) > instant)


def agenda(instant):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    credentials = Credentials.from_authorized_user_file(str(HOME / "google_token.json"))
    service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
    start = instant.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=2)
    items, token = [], None
    while True:
        response = service.events().list(calendarId="primary", timeMin=start.isoformat(),
            timeMax=end.isoformat(), singleEvents=True, orderBy="startTime",
            maxResults=250, pageToken=token).execute(num_retries=0)
        items.extend({k: event.get(k) for k in
            ("id", "summary", "start", "end", "status", "updated")}
            for event in response.get("items", []))
        token = response.get("nextPageToken")
        if not token:
            return items


def tasks(instant):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    credentials = Credentials.from_authorized_user_file(str(HOME / "google_token.json"))
    service = build("tasks", "v1", credentials=credentials, cache_discovery=False)
    lists, token = [], None
    while True:
        response = service.tasklists().list(maxResults=100, pageToken=token).execute(num_retries=0)
        lists.extend(response.get("items", []))
        token = response.get("nextPageToken")
        if not token:
            break
    result = []
    for tasklist in lists:
        token = None
        while True:
            response = service.tasks().list(tasklist=tasklist["id"], maxResults=100,
                showCompleted=False, showHidden=False, pageToken=token).execute(num_retries=0)
            for item in response.get("items", []):
                due = item.get("due", "")[:10]
                if due and (instant.date() - timedelta(days=7)).isoformat() <= due <= (
                        instant.date() + timedelta(days=1)).isoformat():
                    result.append({k: item.get(k) for k in ("id", "title", "due", "updated")})
            token = response.get("nextPageToken")
            if not token:
                break
    return result


def health(instant):
    date = instant.date().isoformat()
    # Only the engine's existing Oura sync is a data write; no invented measurements.
    command = ('set -a; [ ! -f /home/hermes/secrets/health-os.env ] || '
               '. /home/hermes/secrets/health-os.env; set +a; '
               'node src/cli.js sync-daily-source --source oura '
               '--workspace /home/hermes/workspace/health-os-workspace --date "$1"')
    synced = source(lambda: json.loads(run(["bash", "-c", command, "heartbeat", date],
        cwd="/home/hermes/workspace/health-os", timeout=100)))
    base = ["node", "src/cli.js"]
    workspace = ["--workspace", "/home/hermes/workspace/health-os-workspace"]
    return {"sync": synced,
        "today": source(lambda: run(base + ["today"] + workspace + ["--date", date],
            cwd="/home/hermes/workspace/health-os")),
        "weekly": source(lambda: run(base + ["weekly-summary"] + workspace + ["--end-date", date],
            cwd="/home/hermes/workspace/health-os"))}


def learning():
    root = Path("/home/hermes/workspace/learning-os")
    # No pull, publication or changed learner notes during a background check.
    return {"sync": json.loads(run([sys.executable, "tooling/learning.py", "status"], cwd=root)),
        "notes": {name: (root / "vault" / name).read_text()[:16000] for name in
            ("Dashboard.md", "Learner Profile.md", "Coaching Contract.md",
             "Roadmap/12-week-plan.md", "Projects/AI Buddy.md")},
        "latest_sessions": [p.read_text()[:8000] for p in sorted(
            (root / "vault/Sessions").glob("*.md"), key=lambda p: p.stat().st_mtime)[-2:]]}


def jobs():
    raw = read(HOME / "cron/jobs.json", [])
    rows = raw if isinstance(raw, list) else raw.get("jobs", [])
    return [{k: job.get(k) for k in ("id", "name", "enabled", "schedule_display",
        "last_run_at", "last_status", "next_run_at", "failure_streak")} for job in rows]


def git_state(path):
    return {"branch": run(["git", "branch", "--show-current"], cwd=path),
        "head": run(["git", "rev-parse", "HEAD"], cwd=path),
        "origin_main": run(["git", "rev-parse", "origin/main"], cwd=path),
        "dirty": bool(run(["git", "status", "--porcelain"], cwd=path))}


def release():
    request = Request("https://api.github.com/repos/NousResearch/hermes-agent/releases/latest",
                      headers={"User-Agent": "buddy-heartbeat"})
    with urlopen(request, timeout=20) as response:
        value = json.load(response)
    return {k: value.get(k) for k in ("tag_name", "name", "published_at", "html_url")}


def collect(mode):
    instant = now()
    settings = controls()
    if suppressed(settings, instant):
        return {"wakeAgent": False, "reason": "paused"}
    context = {"mode": mode, "date": instant.date().isoformat(), "timezone": "Europe/Warsaw",
        "controls": settings, "jobs": jobs(),
        "focus": read(STATE / "focus.json", []),
        "history": read(STATE / "history.json", {"emitted": [], "feedback": []}),
        "nutrition": {"status": "not_connected", "instruction": "No intake data; infer nothing."}}
    preferences = HOME / "memories/USER.md"
    context["confirmed_preferences"] = preferences.read_text()[:18000] if preferences.exists() else ""
    if mode == "daily":
        context.update(calendar=source(lambda: agenda(instant)), tasks=source(lambda: tasks(instant)),
            health=source(lambda: health(instant)), learning=source(learning),
            projects=source(lambda: run(["npm", "run", "--silent", "idea:status", "--", "--json"],
                cwd="/home/hermes/workspace/idea-maze-engine", timeout=40)))
    else:
        roots = ["/home/hermes/runtimes/hermes-buddy"] + [
            "/home/hermes/workspace/" + name for name in ("health-os", "idea-maze-engine", "learning-os")]
        context.update(repositories={path: source(lambda path=path: git_state(path)) for path in roots},
            service=source(lambda: run(["systemctl", "--user", "is-active", "hermes-buddy.service"])),
            disk=source(lambda: run(["df", "-h", "/home/hermes"])),
            installed_release=source(lambda: run(["git", "describe", "--tags", "--exact-match"],
                cwd=roots[0])), upstream_release=source(release))
    with locked():
        write(STATE / (mode + "-context.json"), context)
    return context


def validate_proposal(value, instant):
    if not isinstance(value, dict) or value.get("date") != instant.date().isoformat():
        raise ValueError("Proposal must be for today's Warsaw date")
    items = value.get("items")
    if not isinstance(items, list) or len(items) > 3:
        raise ValueError("At most three candidate signals")
    for item in items:
        if not isinstance(item, dict) or item.get("topic") not in TOPICS:
            raise ValueError("Invalid topic")
        for field in ("key", "message", "evidence", "why_now"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError("Each signal needs key, message, evidence and why_now")
        if len(item["key"]) > 180 or len(item["message"]) > 450:
            raise ValueError("Signal too long")
        if any(marker in item["message"] for marker in ("[SILENT]", "MEDIA:", "[CRON_FAILURE]")):
            raise ValueError("Transport markers are forbidden")
    if sum(item["topic"] == "buddy" for item in items) > 1:
        raise ValueError("Only one Buddy improvement at a time")
    return value


def choose(proposal, history, settings, instant):
    if suppressed(settings, instant) or not 9 <= instant.hour < 21:
        return []
    if proposal.get("date") != instant.date().isoformat():
        return []
    emitted = history.get("emitted", [])
    if any(row["date"] == instant.date().isoformat() for row in emitted):
        return []
    keys = {key for row in emitted for key in row["keys"]}
    chosen = []
    for item in proposal.get("items", []):
        until = settings.get("snoozes", {}).get(item["topic"])
        if until and datetime.fromisoformat(until) > instant:
            continue
        if item["key"] in keys:
            continue
        if item["topic"] == "buddy" and any("buddy" in row.get("topics", []) and
                datetime.fromisoformat(row["at"]) > instant - timedelta(days=7) for row in emitted):
            continue
        chosen.append(item)
    return chosen[:2]


def deliver():
    instant = now()
    with locked():
        proposal = queued_proposal(instant)
        history = read(STATE / "history.json", {"emitted": [], "feedback": []})
        chosen = choose(proposal, history, controls(), instant)
        if not chosen:
            return ""
        message = "Buddy · " + instant.strftime("%d.%m") + "\n\n" + "\n\n".join(
            item["message"] for item in chosen)
        # A transport reservation, not a claim of successful delivery. Hermes records its ack.
        history["emitted"].append({"date": instant.date().isoformat(), "at": instant.isoformat(),
            "keys": [item["key"] for item in chosen], "topics": [item["topic"] for item in chosen],
            "message_sha256": hashlib.sha256(message.encode()).hexdigest()})
        write(STATE / "history.json", history)
        return message


def queued_proposal(instant):
    installation = read(STATE / "installation.json", {})
    if not installation.get("daily_id"):
        return read(STATE / "pending.json", {"date": "", "items": []})
    output_dir = HOME / "cron/output" / installation["daily_id"]
    outputs = sorted(output_dir.glob("*.md"), key=lambda path: path.stat().st_mtime)
    if not outputs:
        return {"date": "", "items": []}
    text = outputs[-1].read_text()
    if "\n## Response\n" not in text:
        # Paused/wakeAgent=false script gates have no model response.
        return {"date": "", "items": []}
    response = text.rsplit("\n## Response\n", 1)[1].strip()
    value = json.loads(response)
    if not isinstance(value, dict):
        raise ValueError("Native response must be a proposal object")
    if value.get("date") != instant.date().isoformat():
        return {"date": "", "items": []}
    proposal = validate_proposal(value, instant)
    write(STATE / "pending.json", proposal)
    return proposal


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["daily", "weekly", "submit", "deliver", "status",
        "pause", "resume", "snooze", "feedback", "focus"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    if args.action in {"daily", "weekly"}:
        print(json.dumps(collect(args.action), ensure_ascii=False))
    elif args.action == "deliver":
        message = deliver()
        if message:
            print(message)
    elif args.action == "submit":
        value = validate_proposal(json.load(sys.stdin), now())
        with locked():
            write(STATE / "pending.json", value)
        print(json.dumps({"saved": True, "items": len(value["items"])}))
    else:
        with locked():
            settings = controls()
            if args.action == "pause":
                settings["paused"] = not bool(args.value)
                settings["pause_until"] = (now() + timedelta(days=int(args.value))).isoformat() if args.value else None
            elif args.action == "resume":
                settings.update(paused=False, pause_until=None)
            elif args.action == "snooze":
                if args.value not in TOPICS or args.days < 1:
                    raise ValueError("Choose a topic and positive number of days")
                settings.setdefault("snoozes", {})[args.value] = (now() + timedelta(days=args.days)).isoformat()
            elif args.action == "feedback":
                history = read(STATE / "history.json", {"emitted": [], "feedback": []})
                history.setdefault("feedback", []).append({"at": now().isoformat(), "text": args.value})
                write(STATE / "history.json", history)
            elif args.action == "focus":
                value = json.load(sys.stdin)
                if not isinstance(value, list):
                    raise ValueError("Focus is a list of user-confirmed current commitments")
                write(STATE / "focus.json", value)
            if args.action != "status":
                write(STATE / "controls.json", settings)
            print(json.dumps({"controls": settings, "focus": read(STATE / "focus.json", [])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
