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
# %pip install -q lancedb pandas

# %%
import sys, urllib.request, pathlib
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

posts = load("nat_posts.jsonl")
longest = sorted(posts, key=lambda p: -len(p["text"]))[:3]
for p in longest:
    print(p["id"], len(p["text"]), "chars")

# %% [markdown]
# **หั่น** — เลื่อนหน้าต่าง 40 ตัวอักษร ก้าวทีละ 30 (40 − 10 ทับซ้อน)
# แต่ละชิ้นจำว่ามาจากโพสต์ไหน (`parent_id`) ชิ้นที่เท่าไหร่ (`chunk_index`)
# พิมพ์ให้ดูว่าท้ายชิ้นก่อนกับหัวชิ้นถัดไป คือตัวอักษรชุดเดียวกัน

# %%
SIZE, OVERLAP = 40, 10

def chunk(text, size=SIZE, overlap=OVERLAP):
    step = size - overlap
    return [text[i:i + size] for i in range(0, max(len(text) - overlap, 1), step)]

p = longest[0]
for i, c in enumerate(chunk(p["text"])):
    print(f"{p['id']}#{i}  …{c[:10]}|{c[10:-10]}|{c[-10:]}…")

# %% [markdown]
# **เก็บลงตาราง** — vector ของแต่ละชิ้นทำมือเหมือนบทก่อน ๆ
# ชิ้นของโพสต์ไหน ก็ยืม vector ของโพสต์นั้น แล้วขยับนิดหน่อยตามลำดับชิ้น
# (ของจริงใช้โมเดล embed ทีละชิ้น บทที่ 7)

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
print(len(rows), "chunks from", len(longest), "posts")
chunks.to_pandas()[["chunk_id", "parent_id", "chunk_index", "text"]].head(6)

# %% [markdown]
# **ค้นชิ้น** — คำถามทิศ memory `[1, 0, 0]` ขอ 8 ชิ้น
# 6 ชิ้นแรกมาจาก p01 ทั้งหมด ถ้าส่งแบบนี้ให้ agent มันจะเห็นโพสต์เดิมซ้ำ 6 ครั้ง

# %%
hits = chunks.search([1.0, 0.0, 0.0]).limit(8).to_pandas()
hits[["chunk_id", "parent_id", "_distance", "text"]].assign(text=lambda d: d.text.str[:30])

# %% [markdown]
# **ยุบกลับเป็นโพสต์แม่** — group ด้วย `parent_id` เอาชิ้นที่ใกล้ที่สุดเป็นคะแนนของโพสต์
# แล้ว join กลับไปเอาข้อความเต็ม
# นี่คือ pattern "chunk to retrieve, parent to show" ที่ระบบ RAG ทุกตัวใช้

# %%
import duckdb
best = hits.groupby("parent_id", as_index=False).agg(best_distance=("_distance", "min"), best_chunk=("chunk_id", "first"))
parent_df = parents.to_pandas()[["id", "text"]]
duckdb.sql("""
    SELECT b.parent_id, b.best_distance, b.best_chunk, substr(p.text, 1, 50) AS parent_text
    FROM best b JOIN parent_df p ON p.id = b.parent_id
    ORDER BY b.best_distance
""").df()

# %% [markdown]
# บน disk สองตาราง `chunks` แถวเยอะกว่า `posts` แต่ข้อความรวมยาวกว่าเพราะทับซ้อน
# ทับซ้อน 10/40 = จ่ายเพิ่มราว 25% (วัดจริง 27% เพราะชิ้นท้ายของแต่ละโพสต์สั้นไม่เต็ม 40) เพื่อไม่ให้คำขาด

# %%
from pathlib import Path
total_chunk_chars = sum(len(r["text"]) for r in rows)
total_post_chars = sum(len(p["text"]) for p in longest)
print(f"post chars  {total_post_chars}")
print(f"chunk chars {total_chunk_chars}  (+{100 * (total_chunk_chars / total_post_chars - 1):.0f}%)")
for name in ("posts", "chunks"):
    n = sum(f.stat().st_size for f in Path(f"data/{name}.lance/data").glob("*.lance"))
    print(f"{name:<7} {n:>6} bytes on disk")
