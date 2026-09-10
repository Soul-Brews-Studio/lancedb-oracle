# %% [markdown]
# # Lesson 16 — chunking · หั่นข้อความยาวก่อนเก็บ
#
# โพสต์ยาวหนึ่งโพสต์ embed เป็น vector เดียว ความหมายเฉลี่ยกันจนจาง
# หั่นเป็นชิ้นเล็ก แต่ละชิ้นมี vector ของตัวเอง ค้นเจอชิ้น แล้วค่อยเอาโพสต์แม่มาแสดง
# บทนี้ไม่มี API ใหม่ของ LanceDB เลย เป็นเรื่องออกแบบ schema ล้วน ๆ
#
# ภาษาไทยไม่มีช่องว่างระหว่างคำ หั่นตามจำนวนตัวอักษรคือวิธีตรงไปตรงมาที่สุด
# 40 ตัวอักษร ทับซ้อน 10 ตัว เพื่อไม่ให้คำขาดกลางแล้วหายไปทั้งสองฝั่ง
# ตัดตามคำด้วย icu (บทที่ 8) ดีกว่า แต่บทนี้ขอแบบเห็นตัวเลขชัด ๆ ก่อน

# %%
# %pip install -q lancedb pandas duckdb

# %%
import sys, urllib.request, pathlib
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import pandas as pd

posts = load("nat_posts.jsonl")
longest = sorted(posts, key=lambda p: -len(p["text"]))[:3]
pd.DataFrame([{"id": p["id"], "topic": p["topic"], "chars": len(p["text"]), "text": p["text"][:40]} for p in longest])

# %% [markdown]
# **หั่น** — เลื่อนหน้าต่าง 40 ตัวอักษร ก้าวทีละ 30 (40 − 10 ทับซ้อน)
# ตารางข้างล่างคือโพสต์ยาวสุด (p01, 184 ตัวอักษร) หั่นได้ 6 ชิ้น
# ดู column `overlap` = 10 ตัวอักษรท้ายของชิ้นก่อน ต้องเท่ากับ 10 ตัวอักษรแรกของชิ้นนี้ทุกแถว
# ชิ้นสุดท้ายสั้นกว่า 40 เพราะข้อความหมดก่อน

# %%
SIZE, OVERLAP = 40, 10

def chunk(text, size=SIZE, overlap=OVERLAP):
    step = size - overlap
    return [text[i:i + size] for i in range(0, max(len(text) - overlap, 1), step)]

p = longest[0]
pieces = chunk(p["text"])
pd.DataFrame([{
    "chunk_index": i,
    "start": i * (SIZE - OVERLAP),
    "end": i * (SIZE - OVERLAP) + len(c),
    "chars": len(c),
    "overlap (prev tail = this head)": f"{pieces[i-1][-OVERLAP:]} = {c[:OVERLAP]}" if i else "",
    "text": c,
} for i, c in enumerate(pieces)])

# %% [markdown]
# **เก็บลงตาราง** — vector ของแต่ละชิ้นทำมือเหมือนบทก่อน ๆ
# ชิ้นของโพสต์ไหน ก็ยืม vector ของโพสต์นั้น แล้วขยับนิดหน่อยตามลำดับชิ้น
# (ของจริงใช้โมเดล embed ทีละชิ้น บทที่ 7)
# สามโพสต์ได้ 17 ชิ้น ตาราง `chunks` มี `parent_id` ชี้กลับ `posts`

# %%
import lancedb

rows = []
for p in longest:
    for i, c in enumerate(chunk(p["text"])):
        v = [round(x + 0.02 * i, 3) for x in p["vector"]]
        rows.append({"chunk_id": f"{p['id']}#{i}", "parent_id": p["id"], "chunk_index": i, "text": c, "vector": v})

db = lancedb.connect("./data")
chunks = db.create_table("chunks", data=rows, mode="overwrite")
parents = db.create_table("posts", data=longest, mode="overwrite")
summary = pd.DataFrame([{"parent_id": p["id"], "chars": len(p["text"]), "chunks": len(chunk(p["text"]))} for p in longest])
summary.loc[len(summary)] = ["total", summary.chars.sum(), summary.chunks.sum()]
summary

# %% [markdown]
# **ค้นชิ้น** — คำถามทิศ memory `[1, 0, 0]` ขอ 8 ชิ้น
# 6 ชิ้นแรกมาจาก p01 ทั้งหมด (`_distance` 0.02 ถึง 0.14) ถ้าส่งแบบนี้ให้ agent มันจะเห็นโพสต์เดิมซ้ำ 6 ครั้ง
# ชิ้นที่ 7–8 ค่อยเป็น p08

# %%
hits = chunks.search([1.0, 0.0, 0.0]).limit(8).to_pandas()
hits[["chunk_id", "parent_id", "chunk_index", "_distance", "text"]].assign(text=lambda d: d.text.str[:30])

# %% [markdown]
# **ยุบกลับเป็นโพสต์แม่** — group ด้วย `parent_id` เอาชิ้นที่ใกล้ที่สุดเป็นคะแนนของโพสต์
# แล้ว join กลับไปเอาข้อความเต็ม
# 8 ชิ้นกลายเป็น 2 โพสต์ p01 (0.02) กับ p08 (1.62) agent เห็นแต่ละโพสต์ครั้งเดียว พร้อมชิ้นที่ทำให้เจอ
# นี่คือ pattern "chunk to retrieve, parent to show" ที่ระบบ RAG ทุกตัวใช้

# %%
import duckdb
best = hits.groupby("parent_id", as_index=False).agg(best_distance=("_distance", "min"), best_chunk=("chunk_id", "first"), chunks_hit=("chunk_id", "count"))
parent_df = parents.to_pandas()[["id", "topic", "text"]]
duckdb.sql("""
    SELECT b.parent_id, p.topic, b.best_distance, b.chunks_hit, b.best_chunk, substr(p.text, 1, 45) AS parent_text
    FROM best b JOIN parent_df p ON p.id = b.parent_id
    ORDER BY b.best_distance
""").df()

# %% [markdown]
# **ราคาของทับซ้อน** — ตัวอักษรรวมของชิ้นมากกว่าโพสต์ต้นทาง
# ทับซ้อน 10/40 = จ่ายเพิ่มราว 25% (วัดจริง 27% เพราะชิ้นท้ายของแต่ละโพสต์สั้นไม่เต็ม 40) เพื่อไม่ให้คำขาด
# บน disk `chunks` ใหญ่กว่า `posts` ตามนั้น

# %%
from pathlib import Path
chunk_chars = sum(len(r["text"]) for r in rows)
post_chars = sum(len(p["text"]) for p in longest)
pd.DataFrame([
    {"table": "posts", "rows": len(longest), "chars": post_chars, "overhead": "",
     "bytes on disk": sum(f.stat().st_size for f in Path("data/posts.lance/data").glob("*.lance"))},
    {"table": "chunks", "rows": len(rows), "chars": chunk_chars, "overhead": f"+{100 * (chunk_chars / post_chars - 1):.0f}%",
     "bytes on disk": sum(f.stat().st_size for f in Path("data/chunks.lance/data").glob("*.lance"))},
])
