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
import pandas as pd
from pathlib import Path

db = lancedb.connect("./data")

def disk(root: Path):
    """one summary line, then the tree"""
    frags = list((root / "data").glob("*.lance")) if (root / "data").exists() else []
    mans = list((root / "_versions").glob("*.manifest"))
    dels = list((root / "_deletions").glob("*")) if (root / "_deletions").exists() else []
    size = sum(f.stat().st_size for f in root.rglob("*") if f.is_file())
    print(f"fragments={len(frags)} manifests={len(mans)} deletions={len(dels)} bytes={size}")
    def tree(p: Path, prefix=""):
        kids = sorted(p.iterdir(), key=lambda k: (k.is_file(), k.name))
        for i, k in enumerate(kids):
            last = i == len(kids) - 1
            print(prefix + ("└── " if last else "├── ") + k.name)
            if k.is_dir():
                tree(k, prefix + ("    " if last else "│   "))
    tree(root)

# %% [markdown]
# ส่ง list ของ dict เข้าไป schema เดาให้เอง
# ดูตาราง schema ข้างล่าง type เป็น Arrow type `int64` `string` ไม่ใช่ Python `int` `str`

# %%
rows = [
    {"id": 1, "repo": "lance-indexer", "lang": "ts", "stars": 3},
    {"id": 2, "repo": "session-dream", "lang": "ts", "stars": 7},
    {"id": 3, "repo": "arra-memory-py", "lang": "py", "stars": 1},
]
tbl = db.create_table("repos", data=rows, mode="overwrite")
pd.DataFrame([{"column": f.name, "arrow type": str(f.type)} for f in tbl.schema])

# %% [markdown]
# อ่านกลับมาทั้งตาราง 3 แถวเท่าที่ใส่ ลำดับตามที่เขียน

# %%
tbl.to_pandas()

# %% [markdown]
# `where` รับ string หน้าตาเหมือน SQL
# เงื่อนไขถูกดันลงไปตอนอ่านไฟล์ ไม่ได้อ่านทั้งหมดขึ้นมาแล้วค่อยกรอง
# `lang = 'ts'` ควรเหลือ 2 แถว id 1 กับ 2

# %%
tbl.search().where("lang = 'ts'").to_pandas()

# %% [markdown]
# `add` ไม่แก้ไฟล์เดิม เขียน fragment ใหม่ต่อท้าย แล้วออก manifest ใหม่
# ดูตารางข้างล่าง rows 3 → 4 · version 1 → 2

# %%
before = {"step": "after create", "rows": tbl.count_rows(), "version": tbl.version}
tbl.add([{"id": 4, "repo": "lanceglass", "lang": "ts", "stars": 2}])
after = {"step": "after add", "rows": tbl.count_rows(), "version": tbl.version}
pd.DataFrame([before, after])

# %% [markdown]
# เปิด directory ดู บรรทัดแรกคือสรุป บรรทัดถัดไปคือ tree
# `create` หนึ่งครั้ง `add` หนึ่งครั้ง ก็ควรเห็น `fragments=2 manifests=2`
# แต่ละ fragment คือไฟล์ใน `data/` แต่ละ manifest คือไฟล์ใน `_versions/`
#
# ถ้ารัน notebook นี้ซ้ำ จะเห็นมากกว่านั้น
# เพราะ `mode="overwrite"` ไม่ได้ลบของเก่า แค่ออก manifest ใหม่ที่ไม่ชี้ไปหามัน
# ไฟล์เก่ายังอยู่ จนกว่าจะสั่ง cleanup เอง (บทที่ 10)

# %%
disk(Path("data/repos.lance"))
