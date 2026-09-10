# %% [markdown]
# # Lesson 4 — CRUD · เพิ่ม แก้ ลบ upsert
#
# LanceDB ใช้เป็น database ธรรมดาได้ ไม่ต้องมี vector ก็ได้
# บทนี้ทำครบ create · update · delete · upsert แล้วดูว่า disk เปลี่ยนยังไง
# กฎเดิม ไม่มีอะไรถูกเขียนทับ มีแต่เขียนเพิ่ม

# %%
# %pip install -q lancedb pandas

# %%
import lancedb
from pathlib import Path

def tree(root: Path, prefix: str = ""):
    kids = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))
    for i, p in enumerate(kids):
        last = i == len(kids) - 1
        print(prefix + ("└── " if last else "├── ") + p.name)
        if p.is_dir():
            tree(p, prefix + ("    " if last else "│   "))

db = lancedb.connect("./data/lesson4")

# %% [markdown]
# **Create** ตารางไม่มี vector เลย column ธรรมดาสามอัน

# %%
tbl = db.create_table("users", data=[
    {"id": 1, "name": "nat",  "plan": "free"},
    {"id": 2, "name": "beta", "plan": "free"},
    {"id": 3, "name": "thor", "plan": "pro"},
], mode="overwrite")
tbl.to_pandas()

# %% [markdown]
# **Update** ใช้ `where` เลือกแถว `values` บอกค่าใหม่
# แถวที่โดนแก้ไม่ได้ถูกแก้ในที่ Lance เขียนแถวใหม่ แล้ว mark แถวเก่าว่าลบ

# %%
tbl.update(where="id = 2", values={"plan": "pro"})
tbl.to_pandas()

# %% [markdown]
# **Delete** ก็เหมือนกัน ไฟล์ data ไม่ถูกแตะ
# มีไฟล์ใหม่โผล่ใน `_deletions/` บอกว่าแถวไหนไม่ต้องอ่านแล้ว

# %%
tbl.delete("id = 3")
tbl.to_pandas()

# %% [markdown]
# **Upsert** ด้วย `merge_insert` เจอ `id` ซ้ำก็ update ไม่เจอก็ insert
# คำสั่งเดียว ทำสองอย่าง

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
tbl.to_pandas()

# %% [markdown]
# เปิด disk ดู 4 คำสั่ง 4 version
# `_deletions/` คือร่องรอยของ update กับ delete
# แถวที่ "หาย" จากตาราง ยังอยู่ในไฟล์ data เดิมทั้งหมด

# %%
print("version:", tbl.version)
tree(Path("data/lesson4/users.lance"))
