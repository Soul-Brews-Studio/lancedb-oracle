#!/usr/bin/env python3
"""Extract only PUBLIC posts from your own Facebook timeline via the Graph API.

The "Download your information" export carries no privacy field, so this is the
only way to know which posts are public. Needs a user access token with the
`user_posts` permission (Graph API Explorer works for your own account, no app
review needed).

Usage:
    export FB_TOKEN=EAAB...
    python3 tools/fb_public_posts.py --out public_posts.jsonl
    python3 tools/fb_public_posts.py --since 2024-01-01 --all-privacy  # keep every post, label each

Output: one JSON object per line, sorted newest first.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://graph.facebook.com/v21.0"
FIELDS = ",".join([
    "id",
    "created_time",
    "message",
    "story",
    "permalink_url",
    "privacy",
    "status_type",
    "attachments{media_type,type,url,title}",
])
PUBLIC = "EVERYONE"


def get(url: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                err = json.loads(body)["error"]
            except Exception:
                err = {"message": body[:300], "code": e.code}
            # 4 = app rate limit, 17 = user rate limit, 32 = page rate limit
            if err.get("code") in (4, 17, 32) and attempt < retries - 1:
                wait = 60 * (attempt + 1)
                print(f"rate limited, sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            sys.exit(f"Graph API error {err.get('code')}: {err.get('message')}")
    raise RuntimeError("unreachable")


def check_token(token: str) -> str:
    me = get(f"{API}/me?fields=id,name&access_token={token}")
    perms = get(f"{API}/me/permissions?access_token={token}")
    granted = {p["permission"] for p in perms.get("data", []) if p.get("status") == "granted"}
    if "user_posts" not in granted:
        sys.exit(f"token for {me['name']} lacks user_posts permission; granted: {sorted(granted)}")
    return me["name"]


def iter_posts(token: str, since: str | None, until: str | None):
    params = {"fields": FIELDS, "limit": 100, "access_token": token}
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    url = f"{API}/me/posts?{urllib.parse.urlencode(params)}"
    page = 0
    while url:
        page += 1
        data = get(url)
        for post in data.get("data", []):
            yield post
        url = data.get("paging", {}).get("next")
        print(f"page {page}: {len(data.get('data', []))} posts", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="public_posts.jsonl", help="output JSONL path")
    ap.add_argument("--since", help="YYYY-MM-DD, inclusive lower bound")
    ap.add_argument("--until", help="YYYY-MM-DD, upper bound")
    ap.add_argument("--all-privacy", action="store_true", help="keep every post, label instead of filter")
    ap.add_argument("--check", action="store_true", help="only verify the token and exit")
    args = ap.parse_args()

    token = os.environ.get("FB_TOKEN")
    if not token:
        sys.exit("set FB_TOKEN (user access token with user_posts permission)")

    name = check_token(token)
    print(f"token ok: {name}", file=sys.stderr)
    if args.check:
        return

    counts = {}
    kept = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for post in iter_posts(token, args.since, args.until):
            value = post.get("privacy", {}).get("value", "UNKNOWN")
            counts[value] = counts.get(value, 0) + 1
            if not args.all_privacy and value != PUBLIC:
                continue
            post["is_public"] = value == PUBLIC
            f.write(json.dumps(post, ensure_ascii=False) + "\n")
            kept += 1

    total = sum(counts.values())
    print(f"\n{total} posts fetched", file=sys.stderr)
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {v:>5}  {k}", file=sys.stderr)
    print(f"{kept} written to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
