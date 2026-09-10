# %% [markdown]
# # Lesson 1 — first table · ตารางแรก
#
# LanceDB ไม่มี server ตารางหนึ่งคือ directory หนึ่ง
# เขียนหนึ่งครั้ง ได้ไฟล์สามอย่าง `.txn` · `.manifest` · data fragment
# บทนี้สร้างตาราง เพิ่มแถว แล้วเปิด directory ดูว่าเกิดอะไรขึ้นจริง

# %%
# %pip install -q lancedb pandas

# %% [markdown]
# `connect` แค่ชี้ไปที่ folder ยังไม่เกิดไฟล์อะไรทั้งนั้น
# ไม่มี socket ไม่มี port สอง process เปิด folder เดียวกันได้

# %%
import lancedb

db = lancedb.connect("./data")

# %% [markdown]
# ส่ง list ของ dict เข้าไป schema เดาให้เอง
# type ที่ได้เป็น Arrow type (`int64` `string`) ไม่ใช่ Python type

# %%
rows = [
    {"id": 1, "repo": "lance-indexer", "lang": "ts", "stars": 3},
    {"id": 2, "repo": "session-dream", "lang": "ts", "stars": 7},
    {"id": 3, "repo": "arra-memory-py", "lang": "py", "stars": 1},
]
tbl = db.create_table("repos", data=rows, mode="overwrite")
tbl.schema

# %%
tbl.to_pandas()

# %% [markdown]
# `where` รับ string หน้าตาเหมือน SQL
# เงื่อนไขถูกดันลงไปตอนอ่านไฟล์ ไม่ได้อ่านทั้งหมดขึ้นมาแล้วค่อยกรอง

# %%
tbl.search().where("lang = 'ts'").to_pandas()

# %% [markdown]
# `add` ไม่แก้ไฟล์เดิม เขียน fragment ใหม่ต่อท้าย แล้วออก manifest ใหม่
# version เลยขยับจาก 1 เป็น 2

# %%
tbl.add([{"id": 4, "repo": "lanceglass", "lang": "ts", "stars": 2}])
print("count:", tbl.count_rows(), "| version:", tbl.version)

# %% [markdown]
# เปิด directory ดู
# `create` หนึ่งครั้ง `add` หนึ่งครั้ง ก็ควรเห็น txn 2 · manifest 2 · fragment 2
#
# ถ้ารัน notebook นี้ซ้ำ จะเห็นมากกว่านั้น
# เพราะ `mode="overwrite"` ไม่ได้ลบของเก่า แค่ออก manifest ใหม่ที่ไม่ชี้ไปหามัน
# ไฟล์เก่ายังอยู่ จนกว่าจะสั่ง cleanup เอง (บทที่ 5)

# %%
from pathlib import Path

def tree(root: Path, prefix: str = ""):
    kids = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))
    for i, p in enumerate(kids):
        last = i == len(kids) - 1
        print(prefix + ("└── " if last else "├── ") + p.name)
        if p.is_dir():
            tree(p, prefix + ("    " if last else "│   "))

tree(Path("data/repos.lance"))
