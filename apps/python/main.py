# Same tiny app as apps/bun and apps/node, on Python with lancedb 0.38.0.
# Run: uv run main.py
import json
from pathlib import Path

import lancedb
import pandas as pd

posts = [json.loads(l) for l in Path("../../lessons/data/nat_posts.jsonl").read_text().splitlines() if l.strip()]

# 1. connect = pick a folder. Same directory format bun and node wrote.
db = lancedb.connect("./data")
tbl = db.create_table("posts", data=posts, mode="overwrite")
print(f"created  rows={tbl.count_rows()} version={tbl.version}")

# 2. upsert: p11 exists -> update; p12 is new -> insert
(
    tbl.merge_insert("id")
    .when_matched_update_all()
    .when_not_matched_insert_all()
    .execute([
        {**posts[10], "topic": "hardware", "text": posts[10]["text"] + " (edited)"},
        {"id": "p12", "date": "2026-09-10", "topic": "memory", "vector": [0.95, 0.05, 0.0], "text": "Lance Oracle เปิดสอน LanceDB บทที่ 1-20 แล้วครับ"},
    ])
)
print(f"upserted rows={tbl.count_rows()} version={tbl.version}")

# 3. vector search: nearest to the "memory" direction, then hardware only (prefilter)
q = [1.0, 0.0, 0.0]
show = lambda df: print(df[["id", "topic", "_distance", "text"]].assign(text=lambda d: d.text.str[:40]).round({"_distance": 2}).to_string(index=False))
print("nearest to [1,0,0]:"); show(tbl.search(q).limit(3).to_pandas())
print("nearest, topic = hardware:"); show(tbl.search(q).where("topic = 'hardware'").limit(3).to_pandas())

# 4. disk: one manifest per commit, one fragment per write
d = Path("data/posts.lance")
n = lambda sub, ext: len(list((d / sub).glob(f"*{ext}")))
size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
print(f"disk     fragments={n('data', '.lance')} manifests={n('_versions', '.manifest')} txn={n('_transactions', '.txn')} bytes={size}")
