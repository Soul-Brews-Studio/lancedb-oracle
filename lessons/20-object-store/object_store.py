# %% [markdown]
# # Lesson 20 — object store · โค้ดเดิม เปลี่ยนแค่ path
#
# Lance เขียนไฟล์ผ่าน `object_store` ของ Rust local disk กับ S3 คือ backend สองตัวของ layer เดียวกัน
# บทนี้รันโค้ดชุดเดียว บน (1) folder ธรรมดา (2) S3 จำลองด้วย `moto` ในเครื่อง
# แล้วดูว่า fragment กับ manifest ลงไปใน bucket หน้าตาเดิมเป๊ะ
# (3) LanceDB Cloud โชว์แค่วิธี connect ไม่ได้รันจริง

# %%
# %pip install -q lancedb pandas "moto[server]" boto3

# %%
import sys, urllib.request, pathlib
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import pandas as pd
import lancedb
posts = load("nat_posts.jsonl")
results = []

def demo(db, label):
    tbl = db.create_table("posts", data=posts, mode="overwrite")
    tbl.add([{"id": "p12", "date": "2026-09-10", "topic": "memory", "vector": [0.9, 0.1, 0.0], "text": "added after create"}])
    hit = tbl.search([1.0, 0.0, 0.0]).limit(1).to_list()[0]
    results.append({"backend": label, "rows": tbl.count_rows(), "version": tbl.version,
                    "nearest id": hit["id"], "nearest text": hit["text"][:30]})
    return pd.DataFrame(results)

# %% [markdown]
# **(1) local** — เหมือนทุกบทที่ผ่านมา create 11 แถว add 1 แถว search 1 ครั้ง
# ได้ 12 แถว version 2 ใกล้สุดคือ p02

# %%
demo(lancedb.connect("./data/local"), "local")

# %% [markdown]
# **(2) S3** — เปิด `moto_server` เป็น S3 ปลอมบน port 5555 สร้าง bucket ด้วย boto3
# แล้ว connect ด้วย `s3://` + `storage_options`
# key ชื่อตาม `object_store` crate: `aws_endpoint` `aws_access_key_id` `aws_secret_access_key` `aws_region` `allow_http`
# `allow_http` ต้องเปิดเพราะ moto ไม่มี TLS S3 จริงไม่ต้องใส่
# แถวใหม่ในตารางต้องได้ตัวเลขเดียวกับ local ทุกช่อง ต่างแค่ `backend`

# %%
import subprocess, time, atexit, boto3

moto = subprocess.Popen([sys.executable, "-m", "moto.server", "-p", "5555"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
atexit.register(moto.terminate)   # killed even if a later cell fails
time.sleep(2)

s3 = boto3.client("s3", endpoint_url="http://127.0.0.1:5555",
                  aws_access_key_id="x", aws_secret_access_key="x", region_name="us-east-1")
s3.create_bucket(Bucket="lessons")

opts = {"aws_endpoint": "http://127.0.0.1:5555", "aws_access_key_id": "x", "aws_secret_access_key": "x",
        "aws_region": "us-east-1", "allow_http": "true"}
try:
    df = demo(lancedb.connect("s3://lessons/lance", storage_options=opts), "s3 (moto)")
except Exception:
    moto.terminate(); raise
df

# %% [markdown]
# **ใน bucket มีอะไร** — directory เดิม `_transactions/` `_versions/` `data/` แค่กลายเป็น key ใน S3
# สองแถวแรกคือ txn สองครั้ง (create + add) ถัดมา manifest สองอัน แล้ว fragment สองไฟล์
# สังเกต `latest_version_hint.json` ไม่มีบน S3 เพราะ object store ไม่ต้องใช้ hint ใช้ list แล้วเอาชื่อน้อยสุดแทน

# %%
objs = s3.list_objects_v2(Bucket="lessons")["Contents"]
pd.DataFrame([{"key": o["Key"].replace("lance/posts.lance/", ""), "size": o["Size"]} for o in objs])

# %% [markdown]
# **เทียบสอง backend ไฟล์ต่อไฟล์** — ชนิดไฟล์และจำนวนเท่ากัน ขนาดรวมต่างกันแค่ hint file
# นี่คือหลักฐานว่า Lance ไม่รู้ว่าตัวเองอยู่บน S3 มันเขียน key เหมือนเขียน path

# %%
from pathlib import Path
local_files = [p for p in Path("data/local/posts.lance").rglob("*") if p.is_file()]
kind = lambda name: "txn" if name.endswith(".txn") else "manifest" if name.endswith(".manifest") else "fragment" if name.endswith(".lance") else "hint"
rows = []
for label, names, sizes in [("local", [p.name for p in local_files], [p.stat().st_size for p in local_files]),
                            ("s3 (moto)", [o["Key"] for o in objs], [o["Size"] for o in objs])]:
    counts = {}
    for n, s in zip(names, sizes):
        k = kind(n); counts.setdefault(k, [0, 0]); counts[k][0] += 1; counts[k][1] += s
    rows.append({"backend": label, **{f"{k} files": v[0] for k, v in sorted(counts.items())}, "total bytes": sum(sizes)})
pd.DataFrame(rows).fillna(0).astype({c: int for c in ("fragment files", "hint files", "manifest files", "txn files")})

# %% [markdown]
# **(3) LanceDB Cloud** — บริษัทเดียวกันโฮสต์ให้ ไม่ได้รันในบทนี้ (ต้องมี api key)
#
# ```python
# db = lancedb.connect("db://my-project", api_key="ldb_...", region="us-east-1")
# tbl = db.create_table("posts", data=posts)   # โค้ดที่เหลือเหมือนเดิมทุกบรรทัด
# ```
#
# ต่างจาก S3 ตรงที่ Cloud รัน compaction กับ index ให้เอง และรับ writer หลายตัวโดยไม่ต้อง retry ฝั่งเรา

# %% [markdown]
# | | local | S3 (self-host) | LanceDB Cloud |
# |---|---|---|---|
# | latency ต่อ query | ต่ำสุด (mmap) | สูงกว่า ทุก fragment คือ HTTP GET | กลาง มี cache ฝั่ง server |
# | writer หลายตัว | ได้ ผ่าน manifest retry (บทที่ 18) | ได้ แต่ retry ช้ากว่า เพราะ list/put ช้า | server จัดคิวให้ |
# | ค่าใช้จ่าย | disk ในเครื่อง | เก็บถูก แต่ request มีค่า | ตามแผน จ่ายรายเดือน |
# | ใคร compaction | เราเอง (บทที่ 10) | เราเอง ต้องมี job | เขาทำให้ |
# | เหมาะกับ | dev · agent ในเครื่องเดียว | fleet หลายเครื่อง แชร์ตารางเดียว | ไม่อยากดูแล index เอง |
#
# fleet ตอนนี้ทั้งหมดคือ local เครื่องใครเครื่องมัน
# จุดที่จะย้ายไป S3 คือตอนที่ oracle สองตัวบนสองเครื่องต้องเห็นความจำเดียวกัน

# %%
moto.terminate()
moto.wait(timeout=5)
pd.DataFrame([{"moto server": "stopped", "exit code": moto.returncode}])
