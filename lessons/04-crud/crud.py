# %% [markdown]
# # Lesson 4 — CRUD · เพิ่ม แก้ ลบ upsert
#
# LanceDB ใช้เป็น database ธรรมดาได้ ไม่ต้องมี vector ก็ได้
# บทนี้ทำครบ create · update · delete · upsert แล้วดูว่า disk เปลี่ยนยังไง
# กฎเดิม ไม่มีอะไรถูกเขียนทับ มีแต่เขียนเพิ่ม
# ทุกขั้นจะเห็น 2 อย่าง: ตารางที่ผู้ใช้เห็น กับ version/fragment ที่ disk เห็น

# %%
# %pip install -q lancedb pandas

# %%
import lancedb
import pandas as pd
from pathlib import Path
from IPython.display import display

db = lancedb.connect("./data")
log = []

def show(step):
    """print one state line, log it, display the table"""
    m = tbl.list_versions()[-1]["metadata"]
    row = {"step": step, "version": tbl.version, "rows": tbl.count_rows(),
           "data files": int(m["total_data_files"]), "deletion files": int(m["total_deletion_files"])}
    log.append(row)
    print(f"v{row['version']}  {step}: rows={row['rows']} data_files={row['data files']} deletion_files={row['deletion files']}")
    display(tbl.to_pandas())

def disk(root: Path):
    frags = list((root / "data").glob("*.lance"))
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
# **Create** ตารางไม่มี vector เลย column ธรรมดาสามอัน
# บรรทัดสรุปบอก v1 · 3 แถว · 1 data file · 0 deletion file

# %%
tbl = db.create_table("users", data=[
    {"id": 1, "name": "nat",  "plan": "free"},
    {"id": 2, "name": "beta", "plan": "free"},
    {"id": 3, "name": "thor", "plan": "pro"},
], mode="overwrite")
show("create")

# %% [markdown]
# **Update** ใช้ `where` เลือกแถว `values` บอกค่าใหม่
# beta: free → pro
# แถวที่โดนแก้ไม่ได้ถูกแก้ในที่ Lance เขียนแถวใหม่ (data file 1 → 2) แล้ว mark แถวเก่าว่าลบ (deletion file 0 → 1)
# แถวยัง 3 เท่าเดิม version 1 → 2

# %%
tbl.update(where="id = 2", values={"plan": "pro"})
show("update id=2 plan=pro")

# %% [markdown]
# **Delete** ก็เหมือนกัน ไฟล์ data ไม่ถูกแตะ
# thor หายจากตาราง rows 3 → 2 แต่ data file ยัง 2 ไฟล์ deletion file ยัง 1
# (thor อยู่ fragment เดียวกับ beta เดิม ป้ายลบของ fragment นั้นถูกออกใหม่ให้รวม thor ไฟล์เก่ายังอยู่บน disk)
# ตัว thor ยังนอนอยู่ในไฟล์เดิม แค่มีป้ายบอกว่าไม่ต้องอ่าน

# %%
tbl.delete("id = 3")
show("delete id=3")

# %% [markdown]
# **Upsert** ด้วย `merge_insert` เจอ `id` ซ้ำก็ update ไม่เจอก็ insert
# คำสั่งเดียว ทำสองอย่าง: nat team (มีอยู่ → แก้) · odin (ใหม่ → เพิ่ม)
# rows 2 → 3 · version 3 → 4 · deletion file 1 → 0
# เพราะ merge_insert เขียน fragment ใหม่แทน fragment ที่มีป้ายลบ manifest ล่าสุดเลยไม่ต้องชี้ไปที่ป้ายอีก

# %%
(
    tbl.merge_insert("id")
    .when_matched_update_all()
    .when_not_matched_insert_all()
    .execute([
        {"id": 1, "name": "nat", "plan": "team"},  # exists -> update
        {"id": 4, "name": "odin", "plan": "free"},  # new -> insert
    ])
)
show("merge_insert nat->team, +odin")

# %% [markdown]
# **สรุปสี่ขั้น** ตารางเดียว อ่านจากบนลงล่าง
# rows ขึ้น ๆ ลง ๆ (3 → 3 → 2 → 3) แต่ version ขึ้นอย่างเดียว (1 → 4)
# `data files` / `deletion files` ในตารางนี้คือที่ manifest ของ version นั้น**ชี้ไปหา** ไม่ใช่ที่อยู่บน disk
# ดู cell ถัดไป disk มีมากกว่านั้น

# %%
pd.DataFrame(log)

# %% [markdown]
# เปิด disk ดู บรรทัดสรุป: `fragments=3 manifests=4 deletions=2`
# manifest v4 ชี้ไป 2 fragment 0 deletion แต่บน disk มี 3 fragment 2 deletion — ของเก่าไม่ถูกลบ
# `_deletions/` คือร่องรอยของ update กับ delete แถวที่ "หาย" จากตาราง ยังอยู่ในไฟล์ data เดิมทั้งหมด
# จนกว่าจะ optimize (บทที่ 10)

# %%
disk(Path("data/users.lance"))
