# %% [markdown]
# # Lesson 19 — อ่าน Lance โดยไม่ผ่าน LanceDB
#
# `.lance` directory คือสัญญา LanceDB เป็นแค่ client หนึ่งตัว
# บทนี้อ่านตารางเดิม 11 โพสต์ สามทาง ไม่มี `tbl.search()` สักบรรทัด
# Polars · DuckDB บน Arrow · แล้วก็อ่าน directory ตรง ๆ ด้วย `pylance` ไม่ import lancedb เลย
# ทุกทางต้องได้ตัวเลขเดียวกัน memory 5 · agents 3 · hardware 3

# %%
# %pip install -q lancedb pandas polars duckdb pylance

# %%
import sys, urllib.request, pathlib
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import pandas as pd
import lancedb
db = lancedb.connect("./data")
tbl = db.create_table("posts", data=load("nat_posts.jsonl"), mode="overwrite")
tbl.to_pandas()[["id", "topic", "date", "text"]].assign(text=lambda d: d.text.str[:40]).head(4)

# %% [markdown]
# **(a) Polars** — `to_polars()` มีให้ตรง ๆ ใน 0.38 ได้ LazyFrame
# ต่อ `.filter` `.group_by` ของ Polars ได้เลย ตารางข้างล่างคือจำนวนโพสต์ต่อหัวข้อกับวันแรก

# %%
import polars as pl
via_polars = tbl.to_polars().group_by("topic").agg(pl.len().alias("n"), pl.col("date").min().alias("first_post")).sort("topic").collect()
via_polars

# %% [markdown]
# **(b) DuckDB บน Arrow** — เหมือนบทที่ 5 `to_arrow()` แล้วตั้งชื่อใน SQL ได้ทันที
# ตัวเลขเดียวกับ Polars

# %%
import duckdb
posts = tbl.to_arrow()
via_duckdb = duckdb.sql("SELECT topic, count(*) n, min(date) first_post FROM posts GROUP BY topic ORDER BY topic").df()
via_duckdb

# %% [markdown]
# **(c) ไม่มี lancedb เลย** — DuckDB มี community extension `lance` อ่าน directory ได้ตรง
# แต่ยังไม่มี build ให้ทุก platform ลองก่อน ถ้าไม่มีก็ใช้ `pylance` (`import lance`)
# ซึ่งคือ Rust core ตัวเดียวกับที่ LanceDB ใช้ข้างใน
# ตารางบอกว่าทางไหนใช้ได้บนเครื่องนี้ กับ error บรรทัดแรกถ้าไม่ได้

# %%
attempts = []
try:
    duckdb.sql("INSTALL lance FROM community; LOAD lance;")
    ext = duckdb.sql("SELECT topic, count(*) n FROM lance_scan('data/posts.lance') GROUP BY topic ORDER BY topic").df()
    attempts.append({"reader": "duckdb lance extension", "works here?": "✓", "note": f"{len(ext)} topics"})
except Exception as e:
    attempts.append({"reader": "duckdb lance extension", "works here?": "✗", "note": str(e).splitlines()[0][:80]})

import lance
ds = lance.dataset("data/posts.lance")
attempts.append({"reader": "pylance lance.dataset()", "works here?": "✓", "note": f"version {ds.version}, {ds.count_rows()} rows"})
pd.DataFrame(attempts)

# %% [markdown]
# `pylance` อ่าน directory เดียวกัน filter pushdown ทำงาน ขอเฉพาะ column ที่ต้องการได้
# ผลคือ hardware 3 แถว p09 p10 p11

# %%
via_lance = ds.to_table(columns=["id", "topic", "date", "text"], filter="topic = 'hardware'").to_pandas()
via_lance.assign(text=lambda d: d.text.str[:40])

# %% [markdown]
# **สรุปสามทาง** — ทุกทางเห็นข้อมูลเดียวกัน ต่างกันที่ต้อง import อะไร
# `lance.dataset` เห็นสิ่งเดียวกับ `lancedb.open_table` เพราะอ่านไฟล์เดียวกัน
# version · fragment · filter pushdown ครบ ที่ไม่มีคือ embedding registry กับ hybrid search นั่นคือของ LanceDB ชั้นบน
#
# ทำไมสำคัญ ตาราง 835 MB ของ `session-dream` ไม่ต้องรอ MCP server ตื่น
# DuckDB หรือ Polars เปิดอ่าน วิเคราะห์ export ได้เลย โดยไม่แตะโค้ดที่เขียนมัน

# %%
pd.DataFrame([
    {"method": "tbl.to_polars()", "needs lancedb?": "yes (to open)", "rows seen": via_polars["n"].sum(), "filter pushdown?": "lazy — yes", "vector search?": "no"},
    {"method": "duckdb over tbl.to_arrow()", "needs lancedb?": "yes (to open)", "rows seen": int(via_duckdb["n"].sum()), "filter pushdown?": "no (Arrow in memory)", "vector search?": "no"},
    {"method": "lance.dataset(path)", "needs lancedb?": "no", "rows seen": ds.count_rows(), "filter pushdown?": "yes", "vector search?": "raw only, no registry"},
    {"method": "lancedb.open_table(path)", "needs lancedb?": "yes", "rows seen": tbl.count_rows(), "filter pushdown?": "yes", "vector search?": "yes + FTS + hybrid"},
])

# %% [markdown]
# ไฟล์ที่ทุกทางอ่าน คือ fragment เดียวกันใน `data/`

# %%
pd.DataFrame([{"fragment file": p.name[:12] + "…", "bytes": p.stat().st_size,
               "seen by lancedb": "✓", "seen by pylance": "✓" if len(ds.get_fragments()) else ""}
              for p in sorted(pathlib.Path("data/posts.lance/data").glob("*.lance"))])
