# %% [markdown]
# # Lesson 19 — อ่าน Lance โดยไม่ผ่าน LanceDB
#
# `.lance` directory คือสัญญา LanceDB เป็นแค่ client หนึ่งตัว
# บทนี้อ่านตารางเดิม 11 โพสต์ สามทาง ไม่มี `tbl.search()` สักบรรทัด
# Polars · DuckDB บน Arrow · แล้วก็อ่าน directory ตรง ๆ ด้วย `pylance` ไม่ import lancedb เลย

# %%
# %pip install -q lancedb pandas polars duckdb pylance

# %%
import sys, urllib.request, pathlib
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import lancedb
db = lancedb.connect("./data")
tbl = db.create_table("posts", data=load("nat_posts.jsonl"), mode="overwrite")
print(tbl.count_rows(), "rows written by lancedb")

# %% [markdown]
# **(a) Polars** — `to_polars()` มีให้ตรง ๆ ใน 0.38 ได้ LazyFrame
# ต่อ `.filter` `.group_by` ของ Polars ได้เลย

# %%
import polars as pl
tbl.to_polars().group_by("topic").agg(pl.len().alias("n"), pl.col("date").min().alias("first")).sort("topic").collect()

# %% [markdown]
# **(b) DuckDB บน Arrow** — เหมือนบทที่ 5 `to_arrow()` แล้วตั้งชื่อใน SQL ได้ทันที

# %%
import duckdb
posts = tbl.to_arrow()
duckdb.sql("SELECT topic, count(*) n, min(date) first_post FROM posts GROUP BY topic ORDER BY topic").df()

# %% [markdown]
# **(c) ไม่มี lancedb เลย** — DuckDB มี community extension `lance` อ่าน directory ได้ตรง
# แต่ยังไม่มี build ให้ทุก platform ลองก่อน ถ้าไม่มีก็ใช้ `pylance` (`import lance`)
# ซึ่งคือ Rust core ตัวเดียวกับที่ LanceDB ใช้ข้างใน

# %%
try:
    duckdb.sql("INSTALL lance FROM community; LOAD lance;")
    print(duckdb.sql("SELECT topic, count(*) n FROM lance_scan('data/posts.lance') GROUP BY topic").df())
except Exception as e:
    print("duckdb lance extension:", str(e).splitlines()[0][:110])

# %%
import lance
ds = lance.dataset("data/posts.lance")
print("version:", ds.version, "| rows:", ds.count_rows())
ds.to_table(columns=["id", "topic", "date"], filter="topic = 'hardware'").to_pandas()

# %% [markdown]
# `lance.dataset` เห็นสิ่งเดียวกับ `lancedb.open_table` เพราะอ่านไฟล์เดียวกัน
# version · fragment · filter pushdown ครบ ที่ไม่มีคือ embedding registry กับ hybrid search นั่นคือของ LanceDB ชั้นบน
#
# ทำไมสำคัญ ตาราง 835 MB ของ `session-dream` ไม่ต้องรอ MCP server ตื่น
# DuckDB หรือ Polars เปิดอ่าน วิเคราะห์ export ได้เลย โดยไม่แตะโค้ดที่เขียนมัน

# %%
print("same files:", sorted(p.name[:8] for p in pathlib.Path("data/posts.lance/data").glob("*.lance")))
print("fragments per lance:", len(ds.get_fragments()))
