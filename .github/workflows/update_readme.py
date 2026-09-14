"""Refresh the ACTIVITY (GitHub public events) and BLOG (dev.to RSS) sections
of README.md. Never fails the run: on any error it keeps existing content.
Stdlib only.
"""
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET

README = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "README.md"))

USERNAME = "rodriveiga01"
DEVTO_FEED = f"https://dev.to/feed/{USERNAME}"
EVENTS_URL = f"https://api.github.com/users/{USERNAME}/events/public?per_page=20"

FALLBACK_ACTIVITY = [
    "🚧 Building `revien-ios` — offline sync + 1080×1920 export",
    "📦 Porting to `revien-android` — same offline contract",
]


def fetch(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "readme-dynamic"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read()


def get_activity_lines():
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"User-Agent": "readme-dynamic", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        data = json.loads(fetch(EVENTS_URL, headers))
    except Exception:
        return list(FALLBACK_ACTIVITY)
    lines = []
    seen = set()
    for ev in data:
        repo = (ev.get("repo") or {}).get("name", "")
        if not repo or repo == f"{USERNAME}/{USERNAME}":
            continue
        typ = ev.get("type", "")
        if typ == "PushEvent":
            n = len((ev.get("payload") or {}).get("commits", []))
            text = f"⬆️ Pushed {n} commit{'s' if n != 1 else ''} to `{repo}`"
        elif typ == "PullRequestEvent":
            action = (ev.get("payload") or {}).get("action", "")
            text = f"🔀 PR {action} in `{repo}`"
        elif typ == "CreateEvent":
            ref = (ev.get("payload") or {}).get("ref_type", "")
            text = f"🌱 New {ref} in `{repo}`"
        elif typ == "IssuesEvent":
            action = (ev.get("payload") or {}).get("action", "")
            text = f"🐛 Issue {action} in `{repo}`"
        elif typ == "ReleaseEvent":
            text = f"🚀 Release in `{repo}`"
        elif typ == "ForkEvent":
            text = f"🍴 Forked `{repo}`"
        elif typ == "WatchEvent":
            text = f"⭐ Starred `{repo}`"
        else:
            continue
        if text not in seen:
            seen.add(text)
            lines.append(text)
        if len(lines) == 5:
            break
    return lines or list(FALLBACK_ACTIVITY)


def get_blog_lines():
    try:
        xml = fetch(DEVTO_FEED)
        root = ET.fromstring(xml)
        lines = []
        for item in root.iter("item")[:3]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if title and link:
                lines.append(f"- [{title}]({link})")
        return lines or None
    except Exception:
        return None


def replace_block(content, marker, lines):
    pattern = re.compile(
        rf"(<!-- {marker}:START -->).*?(<!-- {marker}:END -->)", re.DOTALL
    )
    body = "\n".join(lines)
    return pattern.sub(rf"\1\n{body}\n\2", content)


def main():
    with open(README) as f:
        content = f.read()
    updated = replace_block(content, "ACTIVITY", get_activity_lines())
    blog = get_blog_lines()
    if blog:
        updated = replace_block(updated, "BLOG", blog)
    if updated != content:
        with open(README, "w") as f:
            f.write(updated)
        print("README.md updated")
    else:
        print("README.md unchanged")


if __name__ == "__main__":
    main()
