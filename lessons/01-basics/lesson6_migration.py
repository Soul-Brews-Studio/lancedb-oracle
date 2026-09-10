# %% [markdown]
# # Lesson 6 — schema migration · เปลี่ยน schema แล้วย้อนกลับได้
#
# เพิ่ม column · เปลี่ยนชื่อ · ลบ column แต่ละอย่างคือ version ใหม่
# ทำพลาดก็ `restore` กลับไป version ก่อนหน้า ไม่ต้องมี migration file ย้อนกลับ
# บทนี้ทำทั้งชุด แล้วดู version ทีละขั้น

# %%
# %pip install -q lancedb pandas

# %%
import lancedb

db = lancedb.connect("./data/lesson6")
tbl = db.create_table("users", data=[
    {"id": 1, "name": "nat",  "plan": "team"},
    {"id": 2, "name": "beta", "plan": "pro"},
], mode="overwrite")

def show(label):
    print(f"--- v{tbl.version} {label}")
    print(tbl.to_pandas().to_string(index=False))

show("start")

# %% [markdown]
# **Add column** ค่าเริ่มต้นเขียนเป็น SQL expression
# ใส่ค่าคงที่ก็ได้ คำนวณจาก column เดิมก็ได้

# %%
tbl.add_columns({"credits": "0", "name_upper": "upper(name)"})
show("add_columns")

# %% [markdown]
# **Rename** ผ่าน `alter_columns` ระบุ `path` เดิม กับ `rename` ใหม่
# ไฟล์ data ไม่ถูกเขียนใหม่ เปลี่ยนแค่ใน manifest

# %%
tbl.alter_columns({"path": "plan", "rename": "tier"})
show("rename plan -> tier")

# %% [markdown]
# **Change type** `alter_columns` รับ `data_type` ก็จริง
# แต่ cast ข้ามตระกูล int → float Lance 0.38 ปฏิเสธ
# ลองดูก่อน อ่าน error ให้ครบ

# %%
import pyarrow as pa
try:
    tbl.alter_columns({"path": "credits", "data_type": pa.float64()})
except ValueError as e:
    print("refused:", e)

# %% [markdown]
# วิธีที่ใช้ได้จริง สามขั้น
# add column ใหม่ที่ cast มาจากของเก่า → drop ของเก่า → rename ใหม่ให้ชื่อเดิม
# ได้ 3 version แต่ทุกขั้นย้อนได้

# %%
tbl.add_columns({"credits_f": "CAST(credits AS DOUBLE)"})
tbl.drop_columns(["credits"])
tbl.alter_columns({"path": "credits_f", "rename": "credits"})
print(tbl.schema.field("credits"))
show("credits int64 -> float64")

# %% [markdown]
# **Drop column** ลบออกจาก schema
# ข้อมูลใน fragment เดิมยังอยู่ แค่ manifest ไม่ชี้ไปหาอีก

# %%
tbl.drop_columns(["name_upper"])
show("drop name_upper")

# %% [markdown]
# **ดูประวัติ** ทุก version มี timestamp
# manifest แต่ละอันคือ snapshot ของ schema + fragment ที่ใช้อยู่ตอนนั้น

# %%
for v in tbl.list_versions():
    m = v["metadata"]
    print(f"v{v['version']}  data_files={m['total_data_files']}  bytes={m['total_files_size']}")

# %% [markdown]
# **ย้อนดู** `checkout(1)` เปิด version 1 แบบอ่านอย่างเดียว
# เห็น schema แรกสุด `plan` ยังอยู่ `credits` ยังไม่มี

# %%
tbl.checkout(1)
show("checkout 1 (read-only)")

# %% [markdown]
# **Restore** ทำให้ version ที่ checkout อยู่ กลายเป็น version ล่าสุด
# ไม่ได้ลบ version กลางทาง แค่สร้าง version ใหม่ที่หน้าตาเหมือน version 1
# Nothing is Deleted

# %%
tbl.restore()
show("after restore")
print("versions kept:", [v["version"] for v in tbl.list_versions()])
