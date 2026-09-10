# %% [markdown]
# # Lesson 17 — retention · ลบแล้วยังไม่หาย จนกว่าจะ cleanup
#
# `delete()` ซ่อนแถว ไม่ได้ลบไฟล์ (บทที่ 4)
# `optimize()` ค่อยรวม fragment แล้วทิ้ง version เก่า ถึงตอนนั้นข้อมูลถึงหายจริง
# ระหว่างสองจังหวะนี้มีช่องว่าง `checkout()` ย้อนไปเห็นแถวที่ลบได้
# นโยบายเก็บข้อมูล (retention) ของ agent memory อยู่ตรงช่องว่างนี้
#
# บทนี้มีตารางเดียวที่โตทีละแถว ทุกขั้นเพิ่มหนึ่งแถวลงไป ดู column ไหนขยับ

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
import pandas as pd
import lancedb

rows = [dict(p, ts=int(dt.datetime.fromisoformat(p["date"]).timestamp())) for p in load("nat_posts.jsonl")]
db = lancedb.connect("./data")
tbl = db.create_table("posts", data=rows, mode="overwrite")

log = []

def snapshot(step):
    root = Path("data/posts.lance")
    size = lambda d: sum(f.stat().st_size for f in (root / d).rglob("*") if f.is_file()) if (root / d).exists() else 0
    try:
        tbl.checkout(1); v1 = f"{tbl.count_rows()} rows"
    except Exception as e:
        v1 = "gone: " + str(e).split(".")[0][:40]
    tbl.checkout_latest()
    log.append({"step": step, "version": tbl.version, "rows": tbl.count_rows(),
                "data bytes": size("data"), "deletion bytes": size("_deletions"),
                "manifests": len(list((root / "_versions").glob("*.manifest"))), "checkout(1) sees": v1})
    return pd.DataFrame(log)

snapshot("start")

# %% [markdown]
# **ลบของเก่า** — เก็บเฉพาะโพสต์ตั้งแต่ 2026-07-01
# แถว 11 → 5 แต่ `data bytes` ยังเท่าเดิม 5220 มี `deletion bytes` โผล่มาแทน
# และ `checkout(1) sees` ยัง 11 rows — version 1 ยังอยู่ครบ

# %%
CUTOFF = int(dt.datetime(2026, 7, 1).timestamp())
tbl.delete(f"ts < {CUTOFF}")
snapshot("delete ts < 2026-07-01")

# %%
tbl.to_pandas()[["id", "date", "topic", "text"]].assign(text=lambda d: d.text.str[:40])

# %% [markdown]
# **ช่องว่าง** — ย้อนไป version 1 ได้ เห็น 11 แถวเหมือนไม่เคยลบ
# ลบไปแล้วก็ยังกู้ได้ ทั้งดีและอันตราย แล้วแต่ว่าใครถาม
# ตารางนี้คือแถวที่ "ลบแล้ว" แต่ยังอ่านได้ 6 แถวก่อน 2026-07-01

# %%
tbl.checkout(1)
recovered = tbl.to_pandas()
tbl.checkout_latest()
recovered[recovered.ts < CUTOFF][["id", "date", "topic", "text"]].assign(text=lambda d: d.text.str[:40])

# %% [markdown]
# **API จริง** — เอกสารเก่าบอกให้ใช้ `compact_files()` กับ `cleanup_old_versions()`
# ทั้งคู่ deprecated แล้ว ดู docstring เอง จะเห็นบอกว่าให้ใช้ `optimize()`

# %%
import inspect
doc = inspect.getdoc(tbl.cleanup_old_versions)
pd.DataFrame([
    {"method": "cleanup_old_versions", "docstring says": next(l.strip() for l in doc.splitlines() if "deprecat" in l.lower())},
    {"method": "compact_files", "docstring says": next(l.strip() for l in inspect.getdoc(tbl.compact_files).splitlines() if "deprecat" in l.lower())},
    {"method": "optimize", "docstring says": "signature " + str(inspect.signature(tbl.optimize))[:70]},
])

# %% [markdown]
# **optimize** ทำสองอย่างในคำสั่งเดียว
# 1. compact — เขียน fragment ใหม่ที่ไม่มีแถวที่ลบ แล้วชี้ manifest ไปหามัน
# 2. cleanup — ทิ้ง version และไฟล์ที่ไม่มีใครชี้แล้ว
# ดูแถวใหม่: `data bytes` 5220 → 3169 · `deletion bytes` → 0 · version 2 → 4 · `checkout(1) sees` กลายเป็น gone
#
# ค่า default `cleanup_older_than` คือ 7 วัน ของที่เพิ่งเขียนจะไม่โดน
# บทนี้ตั้ง `timedelta(0)` + `delete_unverified=True` เพื่อให้เห็นผลทันที
# ในระบบจริงอย่าตั้งแบบนี้ถ้ามี process อื่นกำลังเขียนอยู่

# %%
from datetime import timedelta
tbl.optimize(cleanup_older_than=timedelta(0), delete_unverified=True)
snapshot("optimize(cleanup 0d)")

# %% [markdown]
# **ช่องว่างปิดแล้ว** — `checkout(1)` หา manifest ไม่เจอ error บอกตรง ๆ
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
# version ที่เหลือหลัง cleanup มีแค่ที่ยังถูกชี้อยู่

# %%
pd.DataFrame([{"version": v["version"], "time": v["timestamp"].strftime("%H:%M:%S"),
               "rows in data files": v["metadata"].get("total_rows", "")} for v in tbl.list_versions()])
