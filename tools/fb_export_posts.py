#!/usr/bin/env python3
"""Extract your timeline posts straight from a Facebook "Download your information" zip.

Reads the zip directly (no unzip), fixes Facebook's latin-1 mojibake so Thai text
comes out right, classifies each post as timeline vs group, and writes JSONL.

The export carries NO per-post privacy field. `audience` is always null here;
`account_default_audience` records the account-wide setting at export time from
preferences/privacy_settings.json. To label public vs friends per post you need
tools/fb_public_posts.py (Graph API).

Usage:
    python3 tools/fb_export_posts.py ~/Downloads/facebook-natwrw-2026-09-02-3n8FyPUm.zip --out posts.jsonl
    python3 tools/fb_export_posts.py export.zip --timeline-only --with-text
"""
import argparse
import datetime as dt
import json
import re
import sys
import zipfile

POSTS_RE = re.compile(r"your_facebook_activity/posts/your_posts.*\.json$")
PRIVACY_PATH = "preferences/preferences/privacy_settings.json"
GROUP_RE = re.compile(r" (?:shared|posted) .* to the group: (.+)\.$")
VERB_RE = re.compile(r"^(?:\S+ \S+) (.+?)\.?$")


def fix(s):
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def account_default_audience(z: zipfile.ZipFile) -> str | None:
    try:
        o = json.loads(z.read(PRIVACY_PATH))
    except KeyError:
        return None
    for lv in o.get("label_values", []):
        for item in lv.get("dict", []):
            if item.get("label") == "Who can see your future posts?":
                return fix(item.get("value"))
    return None


def parse_post(p: dict) -> dict:
    title = fix(p.get("title", ""))
    m = GROUP_RE.search(title)
    if m:
        destination, group = "group", m.group(1)
    else:
        destination, group = "timeline", None
    verb = VERB_RE.match(title)
    text = None
    for d in p.get("data", []):
        if "post" in d:
            text = fix(d["post"])
    links, media = [], []
    for att in p.get("attachments", []):
        for d in att.get("data", []):
            if "external_context" in d and d["external_context"].get("url"):
                links.append(d["external_context"]["url"])
            if "media" in d:
                media.append({
                    "uri": d["media"].get("uri"),
                    "title": fix(d["media"].get("title")),
                    "description": fix(d["media"].get("description")),
                })
    ts = p["timestamp"]
    return {
        "ts": ts,
        "date": dt.datetime.fromtimestamp(ts, dt.timezone.utc).astimezone().isoformat(timespec="minutes"),
        "destination": destination,
        "group": group,
        "kind": verb.group(1) if verb else title,
        "text": text,
        "links": links,
        "media": media,
        "audience": None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip", help="facebook-*.zip export")
    ap.add_argument("--out", default="posts.jsonl")
    ap.add_argument("--timeline-only", action="store_true", help="drop posts made into groups")
    ap.add_argument("--with-text", action="store_true", help="keep only posts that have your own text")
    args = ap.parse_args()

    with zipfile.ZipFile(args.zip) as z:
        default_audience = account_default_audience(z)
        files = [n for n in z.namelist() if POSTS_RE.search(n)]
        if not files:
            sys.exit("no your_posts*.json found in zip")
        posts = []
        for n in sorted(files):
            posts.extend(parse_post(p) for p in json.loads(z.read(n)))

    posts.sort(key=lambda p: -p["ts"])
    counts = {"total": len(posts), "timeline": 0, "group": 0, "with_text": 0, "written": 0}
    with open(args.out, "w", encoding="utf-8") as f:
        for p in posts:
            counts[p["destination"]] += 1
            if p["text"]:
                counts["with_text"] += 1
            if args.timeline_only and p["destination"] != "timeline":
                continue
            if args.with_text and not p["text"]:
                continue
            p["account_default_audience"] = default_audience
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
            counts["written"] += 1

    lo, hi = posts[-1]["date"][:10], posts[0]["date"][:10]
    print(f"source files: {len(files)}", file=sys.stderr)
    print(f"range: {lo} .. {hi}", file=sys.stderr)
    print(f"account default audience at export: {default_audience}", file=sys.stderr)
    for k, v in counts.items():
        print(f"  {v:>5}  {k}", file=sys.stderr)
    print(f"-> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
