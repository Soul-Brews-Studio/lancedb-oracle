# %% [markdown]
# # Lesson 15 — scalar index · index บน column ธรรมดา
#
# vector index ช่วย `search(vec)` FTS index ช่วย `search(text)`
# แต่ `where("topic = 'memory' AND ts > ...")` ก็มี index ของตัวเอง
# **BITMAP** สำหรับ column ที่ค่าซ้ำเยอะ (topic มี 3 ค่า) · **BTREE** สำหรับช่วง (ts เป็นตัวเลข)
# 11 แถว index ไม่ได้ช่วยให้เร็วขึ้นหรอก บทนี้ดูว่า query plan เปลี่ยนยังไง

# %%
# %pip install -q lancedb pandas

# %%
import sys, urllib.request, pathlib
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import datetime as dt
import lancedb
from lancedb.index import BTree, Bitmap

# ts = วินาทีตั้งแต่ 1970 ทำจาก date เพื่อให้เปรียบเทียบเป็นตัวเลขได้
rows = [dict(p, ts=int(dt.datetime.fromisoformat(p["date"]).timestamp())) for p in load("nat_posts.jsonl")]
db = lancedb.connect("./data")
tbl = db.create_table("posts", data=rows, mode="overwrite")
tbl.to_pandas()[["id", "date", "ts", "topic"]]

# %% [markdown]
# **ก่อนมี index** — ดู plan ของ query ที่กรอง topic กับช่วงเวลา
# `explain_plan()` คืน string บอกว่า Lance จะทำอะไร ยังไม่รัน
# บรรทัดล่างสุดคือ `LanceRead ... full_filter=...` = อ่าน column topic กับ ts ทุกแถว แล้วค่อยกรองในตัว

# %%
CUTOFF = int(dt.datetime(2026, 7, 1).timestamp())
q = lambda: tbl.search().where(f"topic = 'memory' AND ts > {CUTOFF}").select(["id", "date", "topic"]).limit(10)
print(q().explain_plan())
q().to_pandas()

# %% [markdown]
# **สร้าง index สองอัน**
# API ปัจจุบันคือ `create_index(col, config=Bitmap())` / `BTree()`
# `create_scalar_index(col, index_type="BITMAP")` ยังเรียกได้แต่ deprecated ตั้งแต่ 0.25 เหมือน FTS ในบทที่ 8

# %%
tbl.create_index("topic", config=Bitmap())
tbl.create_index("ts", config=BTree())
for i in tbl.list_indices():
    print(i.name, i.index_type, i.columns)

# %% [markdown]
# **หลังมี index** — query เดิม plan เปลี่ยน
# บรรทัดล่างสุดกลายเป็น `ScalarIndexQuery: AND([topic = memory]@topic_idx(Bitmap), [ts > ...]@ts_idx(BTree))`
# Lance ถาม index ทั้งสองก่อนว่าแถวไหนตรง แล้ว `LanceRead` ข้างบนถึงอ่านเฉพาะแถวนั้น `refine_filter=--` คือไม่ต้องกรองซ้ำ
# ผลลัพธ์เหมือนเดิมทุกแถว ต่างกันแค่วิธีหา

# %%
print(q().explain_plan())
q().to_pandas()

# %% [markdown]
# **ทำไม 11 แถวถึงไม่ควรทำ** — index คือไฟล์เพิ่ม อ่านเพิ่ม
# บน disk แต่ละ index มี directory ของตัวเองใน `_indices/` สองอันรวมกันเกินครึ่งของ data ทั้งตาราง
# จุดคุ้มทุนอยู่ที่หลักหมื่นแถวขึ้นไป หรือเมื่อ `where` ตัดแถวออกได้เกิน 90%
# ความจำ agent ที่กรองด้วย `agent_id` / `session` ทุกครั้ง ถึงตรงนั้นเร็ว

# %%
from pathlib import Path
data_bytes = sum(f.stat().st_size for f in Path("data/posts.lance/data").glob("*.lance"))
print(f"data fragments  {data_bytes:>7} bytes")
for d in sorted(Path("data/posts.lance/_indices").iterdir()):
    n = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
    print(f"index {d.name[:8]}…  {n:>7} bytes")
