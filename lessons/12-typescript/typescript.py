# %% [markdown]
# # Lesson 12 — Python vs TypeScript · ไฟล์เดียวกัน สอง binding
#
# LanceDB ตัวจริงเขียนด้วย Rust Python กับ TypeScript เป็นแค่เปลือกสองชั้นบนไฟล์เดียวกัน
# บทนี้สร้างตารางด้วย Python แล้วเปิด directory เดียวกันด้วย `@lancedb/lancedb` บน bun
# fleet ใช้ TypeScript 16 repo ใช้ Python 1 repo บทนี้คือสะพาน
#
# ต้องมี `bun` ในเครื่อง บน Colab ไม่มี cell ฝั่ง TypeScript จะข้ามไปพร้อมบอกเหตุผล

# %%
# %pip install -q lancedb pandas

# %%
import lancedb

db = lancedb.connect("./data")
tbl = db.create_table("users", data=[
    {"id": 1, "name": "nat",  "plan": "team"},
    {"id": 2, "name": "beta", "plan": "pro"},
    {"id": 3, "name": "odin", "plan": "free"},
], mode="overwrite")
print("python  count:", tbl.count_rows())
print("python  schema:", [f"{f.name}:{f.type}" for f in tbl.schema])
print("python  where :", [r["name"] for r in tbl.search().where("plan != 'free'").limit(10).to_list()])

# %% [markdown]
# **ฝั่ง TypeScript** — `open.ts` เปิด `./data` เดียวกัน ไม่ copy ไม่ export
# `bun run open.ts` แล้วเอา stdout มาแปะในนี้
# API ชื่อคล้ายกัน camelCase แทน snake_case · `toArray()` แทน `to_list()` · ทุกอย่างเป็น `await`

# %%
print(open("open.ts", encoding="utf-8").read())

# %%
import os, shutil, subprocess
bun = shutil.which("bun")
if bun is None:
    print("bun not found on this machine (normal on Colab) — skipping the TypeScript half.")
    print("Run locally: cd lessons/12-typescript && bun install && bun run open.ts")
else:
    if not __import__("pathlib").Path("node_modules").exists():
        subprocess.run([bun, "install", "--silent"], check=True)
    out = subprocess.run([bun, "run", "open.ts"], capture_output=True, text=True, env={**os.environ, "NO_COLOR": "1"})
    print(out.stdout or out.stderr)

# %% [markdown]
# **เทียบชื่อ API** — สิ่งเดียวกัน คนละสะกด
#
# | Python | TypeScript | หมายเหตุ |
# |---|---|---|
# | `lancedb.connect(path)` | `await connect(path)` | TS ทุก call เป็น Promise |
# | `db.create_table(name, data=rows)` | `await db.createTable(name, rows)` | |
# | `db.open_table(name)` | `await db.openTable(name)` | |
# | `tbl.search().where(...).limit(n).to_list()` | `tbl.query().where(...).limit(n).toArray()` | ไม่มี vector = `query()` ใน TS |
# | `tbl.search(vec).limit(n).to_pandas()` | `tbl.search(vec).limit(n).toArray()` | ไม่มี pandas ใน TS |
# | `tbl.count_rows()` | `await tbl.countRows()` | |
# | `tbl.schema` | `await tbl.schema()` | property vs method |
# | `tbl.add(rows)` | `await tbl.add(rows)` | |
# | `tbl.create_index(config=IvfPq(...))` | `tbl.createIndex("vector", { config: Index.ivfPq({...}) })` | |
#
# ไฟล์บน disk เหมือนกันทุก byte สอง process เปิดพร้อมกันได้ นี่คือสิ่งที่ "embedded" หมายถึง

# %%
from pathlib import Path
for f in sorted(Path("data/users.lance/_versions").glob("*.manifest")):
    print(f.name, f.stat().st_size, "bytes — read by both bindings")
