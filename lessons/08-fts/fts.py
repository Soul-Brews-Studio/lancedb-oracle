# %% [markdown]
# # Lesson 8 — full-text search · ค้นด้วยคำ ไม่ใช่ด้วย vector
#
# vector search ตอบว่า "ความหมายใกล้" FTS ตอบว่า "มีคำนี้อยู่จริง"
# คนละ index คนละคะแนน `_score` (BM25 ยิ่งสูงยิ่งดี) แทน `_distance` (ยิ่งต่ำยิ่งดี)
# โพสต์ 11 โพสต์เดิม บทนี้ไม่แตะ vector เลย
#
# ภาษาไทยไม่มีช่องว่างระหว่างคำ tokenizer เลยสำคัญกว่าปกติ บทนี้ลองสามแบบ

# %%
# %pip install -q lancedb pandas

# %%
import sys, urllib.request, pathlib
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import lancedb
from lancedb.index import FTS

db = lancedb.connect("./data")
tbl = db.create_table("posts", data=load("nat_posts.jsonl"), mode="overwrite")

def fts(q):
    df = tbl.search(q, query_type="fts").limit(4).to_pandas()
    return df[["id", "topic", "_score", "text"]].assign(text=lambda d: d.text.str[:42])

# %% [markdown]
# **1. tokenizer `simple`** (ค่า default) ตัดที่ช่องว่างและเครื่องหมาย
# API ปัจจุบันคือ `create_index(col, config=FTS(...))`
# `create_fts_index` ยังเรียกได้แต่ deprecated ตั้งแต่ 0.25

# %%
tbl.create_index("text", config=FTS())
fts("Memory")

# %% [markdown]
# คำอังกฤษเจอ แต่คำไทย "จอ" ที่อยู่ใน p09 p10 แน่ ๆ กลับว่างเปล่า
# เพราะ "มาออกจอเลยครับ" ทั้งก้อนคือ token เดียว "จอ" ไม่ตรงกับอะไร

# %%
fts("จอ")

# %% [markdown]
# **2. tokenizer `icu`** — ตัดคำด้วย Unicode word segmentation รู้จักภาษาไทย
# "มาออกจอเลยครับ" กลายเป็น มา · ออก · จอ · เลย · ครับ
# `replace=True` เพราะสร้างทับ index เดิม

# %%
tbl.create_index("text", config=FTS(base_tokenizer="icu"), replace=True)
fts("จอ")

# %%
fts("ความทรงจำ")   # เจอ p03 ตรง ๆ โพสต์เดียว

# %% [markdown]
# **3. tokenizer `ngram`** — หั่นทุกอย่างเป็นชิ้น 2–3 ตัวอักษร ไม่ต้องรู้ภาษา
# "ความทรงจำ" เจอ p03 คะแนนสูงมาก แต่ p04 p11 p07 ก็โผล่มาด้วย
# เพราะมีชิ้น "ทร" "ควา" ซ้ำกันโดยบังเอิญ ค้นเจอทุกอย่างรวมทั้งขยะ

# %%
tbl.create_index("text", config=FTS(base_tokenizer="ngram", ngram_min_length=2, ngram_max_length=3), replace=True)
fts("ความทรงจำ")

# %% [markdown]
# **สรุปในตารางเดียว** — สร้าง index ทั้งสามแบบอีกรอบ ยิงคำถามชุดเดียวกัน
# แถว = tokenizer คอลัมน์ = คำค้น ช่อง = id ที่เจอ (— คือไม่เจอ)
# `simple` ว่างทุกช่องที่เป็นไทย · `icu` ตรงเป๊ะ · `ngram` เจอเกิน ("ความทรงจำ" ได้ 5 ทั้งที่ควรได้ 1)
# สำหรับความจำ agent ที่มีไทยปน `icu` คือค่าที่ควรตั้ง

# %%
import pandas as pd

TOKENIZERS = {
    "simple": FTS(),
    "icu": FTS(base_tokenizer="icu"),
    "ngram 2-3": FTS(base_tokenizer="ngram", ngram_min_length=2, ngram_max_length=3),
}
QUERIES = ["Memory", "Claude", "จอ", "ความทรงจำ"]
summary = []
for name, cfg in TOKENIZERS.items():
    tbl.create_index("text", config=cfg, replace=True)
    row = {"tokenizer": name}
    for q in QUERIES:
        ids = [h["id"] for h in tbl.search(q, query_type="fts").limit(5).to_list()]
        row[f'"{q}"'] = " ".join(ids) if ids else "—"
    summary.append(row)
pd.DataFrame(summary)

# %% [markdown]
# บน disk index อยู่ใน `_indices/` แยกจาก data fragment
# สร้าง index ทั้งหมด 6 ครั้ง = 6 directory ของเก่าไม่หาย (Nothing is Deleted) มีแค่อันล่าสุดที่ใช้งาน
# `ngram` ใหญ่กว่า `icu` เกือบ 3 เท่า (25.7 KB กับ 9.4 KB) เพราะทุกข้อความแตกเป็นชิ้นเล็กมากกว่า
# `add()` แถวใหม่หลังจากนี้ ไม่เข้า index อัตโนมัติ ต้อง `optimize()` (บทที่ 10)

# %%
from pathlib import Path
live = {i.name for i in tbl.list_indices()}
dirs = sorted(Path("data/posts.lance/_indices").iterdir(), key=lambda p: p.stat().st_mtime)
labels = ["simple", "icu", "ngram 2-3"] * 2
pd.DataFrame([{
    "order": i + 1,
    "tokenizer": labels[i] if i < len(labels) else "?",
    "index dir": d.name[:8] + "…",
    "bytes": sum(f.stat().st_size for f in d.rglob("*") if f.is_file()),
    "live?": "✓" if i == len(dirs) - 1 else "",
} for i, d in enumerate(dirs)])
