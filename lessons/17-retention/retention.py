# %% [markdown]
# # Lesson 17 — retention · ลบแล้วยังไม่หาย จนกว่าจะ cleanup
#
# `delete()` ซ่อนแถว ไม่ได้ลบไฟล์ (บทที่ 4)
# `optimize()` ค่อยรวม fragment แล้วทิ้ง version เก่า ถึงตอนนั้นข้อมูลถึงหายจริง
# ระหว่างสองจังหวะนี้มีช่องว่าง `checkout()` ย้อนไปเห็นแถวที่ลบได้
# นโยบายเก็บข้อมูล (retention) ของ agent memory อยู่ตรงช่องว่างนี้

# %%
# %pip install -q lancedb pandas

# %%
import sys, urllib.request, pathlib
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import datetime as dt
from pathlib import Path
import lancedb

rows = [dict(p, ts=int(dt.datetime.fromisoformat(p["date"]).timestamp())) for p in load("nat_posts.jsonl")]
db = lancedb.connect("./data")
tbl = db.create_table("posts", data=rows, mode="overwrite")

def disk(label):
    root = Path("data/posts.lance")
    parts = {d: sum(f.stat().st_size for f in (root / d).rglob("*") if f.is_file()) if (root / d).exists() else 0
             for d in ("data", "_deletions", "_versions", "_transactions")}
    print(f"{label:<22} v{tbl.version}  rows={tbl.count_rows():>2}  " + "  ".join(f"{k}={v}" for k, v in parts.items()))

disk("start")

# %% [markdown]
# **ลบของเก่า** — เก็บเฉพาะโพสต์ตั้งแต่ 2026-07-01
# หาย 6 แถว เหลือ 5 แต่ `data` ยัง 5220 ไบต์เท่าเดิม มีไฟล์ใน `_deletions` โผล่มาแทน

# %%
CUTOFF = int(dt.datetime(2026, 7, 1).timestamp())
tbl.delete(f"ts < {CUTOFF}")
disk("after delete")
tbl.to_pandas()[["id", "date", "topic"]]

# %% [markdown]
# **ช่องว่าง** — version 1 ยังอยู่ `checkout(1)` เห็น 11 แถวเหมือนเดิม
# ลบไปแล้วก็ยังกู้ได้ ทั้งดีและอันตราย แล้วแต่ว่าใครถาม

# %%
tbl.checkout(1)
print("v1 rows:", tbl.count_rows())
tbl.checkout_latest()
print("latest rows:", tbl.count_rows())

# %% [markdown]
# **API จริง** — เอกสารเก่าบอกให้ใช้ `compact_files()` กับ `cleanup_old_versions()`
# ทั้งคู่ deprecated แล้ว ดู `help()` เอง จะเห็นบอกว่าให้ใช้ `optimize()`

# %%
import inspect
doc = inspect.getdoc(tbl.cleanup_old_versions)
print([l.strip() for l in doc.splitlines() if "deprecat" in l.lower() or "optimize" in l][:2])
print("optimize", inspect.signature(tbl.optimize))

# %% [markdown]
# **optimize** ทำสองอย่างในคำสั่งเดียว
# 1. compact — เขียน fragment ใหม่ที่ไม่มีแถวที่ลบ แล้วชี้ manifest ไปหามัน
# 2. cleanup — ทิ้ง version และไฟล์ที่ไม่มีใครชี้แล้ว
# ผล: `data` 5220 → 3169 ไบต์ `_deletions` กลับเป็น 0 version กระโดดจาก 2 ไป 4 (compact หนึ่ง cleanup หนึ่ง)
#
# ค่า default `cleanup_older_than` คือ 7 วัน ของที่เพิ่งเขียนจะไม่โดน
# บทนี้ตั้ง `timedelta(0)` + `delete_unverified=True` เพื่อให้เห็นผลทันที
# ในระบบจริงอย่าตั้งแบบนี้ถ้ามี process อื่นกำลังเขียนอยู่

# %%
from datetime import timedelta
tbl.optimize(cleanup_older_than=timedelta(0), delete_unverified=True)
disk("after optimize")

# %% [markdown]
# **ช่องว่างปิดแล้ว** — `checkout(1)` หา manifest ไม่เจอ
# แถวที่ลบไป ตอนนี้ไม่มีไฟล์ไหนถืออยู่ นี่คือจุดที่ "ลบ" กลายเป็น "ลบจริง"

# %%
try:
    tbl.checkout(1)
    print("v1 rows:", tbl.count_rows())
except Exception as e:
    print(type(e).__name__, "-", str(e).splitlines()[0][:100])
tbl.checkout_latest()

# %% [markdown]
# สรุปเป็นนโยบาย
#
# | ขั้น | คำสั่ง | ข้อมูลเก่า |
# |---|---|---|
# | ซ่อน | `delete("ts < cutoff")` | ยังอยู่บน disk กู้ได้ด้วย `checkout` |
# | รวม | `optimize()` ส่วน compact | fragment ใหม่ไม่มี แต่ fragment เก่ายังอยู่ |
# | ทิ้ง | `optimize(cleanup_older_than=...)` | หายจริง |
#
# agent memory ที่ต้องมี audit trail ให้ตั้ง `cleanup_older_than` ยาว ๆ
# ที่ต้องลบตามกฎหมาย ให้ตั้งสั้นแล้วรัน optimize ตามรอบ

# %%
for v in tbl.list_versions():
    print(f"v{v['version']}  {v['timestamp'].strftime('%H:%M:%S')}")
