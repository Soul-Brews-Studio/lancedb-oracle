# %% [markdown]
# # Lesson 10 — compaction & cleanup · เก็บกวาดสิ่งที่ append ทิ้งไว้
#
# ทุกบทที่ผ่านมาบอกว่า Lance ไม่เขียนทับ มีแต่เขียนเพิ่ม
# บทนี้ดูว่าเพิ่มไปเรื่อย ๆ แล้วเกิดอะไร fragment เล็ก ๆ กองเต็ม `_deletions/` โต version พอก
# แล้วสั่งเก็บกวาดสองขั้น `compact_files()` รวม fragment · `cleanup_old_versions()` ลบ version เก่า
# สองคำสั่งนี้แยกกัน คนละหน้าที่ ทำทีละอย่างแล้วนับ

# %%
# %pip install -q lancedb pandas

# %%
import sys, urllib.request, pathlib, warnings
warnings.filterwarnings("ignore")   # compact_files / cleanup_old_versions warn "deprecated" — see below
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

from pathlib import Path
import lancedb

db = lancedb.connect("./data")
tbl = db.create_table("posts", data=load("nat_posts.jsonl"), mode="overwrite")

def state(label):
    root = Path("data/posts.lance")
    frags = len(list((root / "data").glob("*.lance")))
    dels = len(list((root / "_deletions").glob("*"))) if (root / "_deletions").exists() else 0
    vers = len(list((root / "_versions").glob("*.manifest")))
    size = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
    print(f"{label:<22} rows={tbl.count_rows():<3} fragments={frags:<3} deletions={dels:<3} versions={vers:<3} bytes={size}")

state("start")

# %% [markdown]
# **กองให้ดู** — update 5 ครั้ง add 3 ครั้ง delete 2 ครั้ง รวม 10 การเขียน
# ทุก `add` = fragment ใหม่ ทุก `update`/`delete` = ไฟล์ใน `_deletions/` ทุกอย่าง = version ใหม่
# ตารางมีแค่ 11 แถว แต่บน disk เหมือนตารางที่ถูกเขียน 11 ครั้ง

# %%
for i in range(5):
    tbl.update(where=f"id = 'p0{i + 1}'", values={"topic": "memory"})
for i in range(3):
    tbl.add([{"id": f"x{i}", "date": "2026-09-10", "topic": "agents", "vector": [0.0, 1.0, 0.0], "text": f"extra {i}"}])
tbl.delete("id = 'x0'")
tbl.delete("id = 'x1'")
state("after 10 writes")

# %% [markdown]
# **ขั้นที่ 1 — `compact_files()`** รวม fragment เล็ก ๆ เป็นก้อนเดียว
# แถวที่ถูก mark ลบไว้ ถูกทิ้งจริงตอนเขียนก้อนใหม่ manifest ล่าสุดชี้ไป fragment เดียว
# แต่บน disk ยังนับได้ 10 fragment 5 deletion file เพราะไฟล์เก่าไม่ถูกลบ version เพิ่มอีกสอง bytes ยิ่งโต
# ตั้งแต่ 0.21 คำสั่งนี้ถูกทำเครื่องหมาย deprecated ให้ใช้ `optimize()` แทน ยังเรียกได้ เอาไว้ดูทีละขั้น

# %%
stats = tbl.compact_files()
print(stats)
state("after compact_files")

# %% [markdown]
# **ขั้นที่ 2 — `cleanup_old_versions()`** ลบ manifest กับ fragment ที่ไม่มี version ไหนชี้ถึงแล้ว
# `older_than=timedelta(0)` = ลบทุก version ที่ไม่ใช่ล่าสุด ปกติใส่ 7 วันเผื่อ reader ที่ค้างอยู่
# ตรงนี้แหละที่ Nothing is Deleted หยุด เพราะเราสั่งเอง (deprecated ตั้งแต่ 0.21 เช่นกัน)
# ลำดับสำคัญ compact ก่อน cleanup ทีหลัง สลับกันแล้ว cleanup ไม่มีอะไรให้ลบ
# ผลคือกลับมา fragment 1 · deletion 0 · version 1 เท่าตอนเริ่ม แต่ข้อมูลเป็นชุดใหม่

# %%
from datetime import timedelta
stats = tbl.cleanup_old_versions(older_than=timedelta(0))
print(stats)
state("after cleanup")

# %% [markdown]
# **index ก็ค้างได้** — สร้าง FTS index แล้ว `add` แถวใหม่
# ยังค้นเจอ เพราะ Lance สแกน fragment ที่ยังไม่มี index ให้แบบ brute force
# แต่ `index_stats` บอกความจริง `num_unindexed_rows = 1` แถวนั้นอยู่นอก index ค้นช้ากว่า
# `optimize()` = compact + cleanup + เติม index ในคำสั่งเดียว นี่คือคำสั่งที่ 0.38 อยากให้ใช้ ตั้ง schedule วันละครั้ง

# %%
from lancedb.index import FTS
tbl.create_index("text", config=FTS(base_tokenizer="icu"))
tbl.add([{"id": "x9", "date": "2026-09-10", "topic": "agents", "vector": [0.0, 1.0, 0.0], "text": "oracle ตัวใหม่ตื่นแล้ว"}])
s = tbl.index_stats("text_idx")
print("before optimize: found", [h["id"] for h in tbl.search("oracle", query_type="fts").limit(3).to_list()],
      "| indexed", s.num_indexed_rows, "unindexed", s.num_unindexed_rows)
tbl.optimize(cleanup_older_than=timedelta(0))
s = tbl.index_stats("text_idx")
print("after optimize:  found", [h["id"] for h in tbl.search("oracle", query_type="fts").limit(3).to_list()],
      "| indexed", s.num_indexed_rows, "unindexed", s.num_unindexed_rows)
state("after optimize")

# %% [markdown]
# ตารางที่ agent เขียนทุกวันแล้วไม่เคย optimize จะโตแบบ "after 10 writes" ไปเรื่อย ๆ
# ใน fleet มีตาราง 835 MB ที่น่าจะไม่เคยผ่านคำสั่งนี้เลย
# `optimize(cleanup_older_than=timedelta(days=7))` วันละครั้ง คือสิ่งที่บทนี้อยากให้จำ
