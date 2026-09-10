# %% [markdown]
# # Lesson 6 — schema migration · เปลี่ยน schema แล้วย้อนกลับได้
#
# เพิ่ม column · เปลี่ยนชื่อ · ลบ column แต่ละอย่างคือ version ใหม่
# ทำพลาดก็ `restore` กลับไป version ก่อนหน้า ไม่ต้องมี migration file ย้อนกลับ
# บทนี้ทำทั้งชุด ทุกขั้นเห็นตารางพร้อมบรรทัด `v<เลข>` บอกว่าอยู่ version ไหน

# %%
# %pip install -q lancedb pandas

# %%
import lancedb
import pandas as pd
from IPython.display import display

db = lancedb.connect("./data")
tbl = db.create_table("users", data=[
    {"id": 1, "name": "nat",  "plan": "team"},
    {"id": 2, "name": "beta", "plan": "pro"},
], mode="overwrite")

def show(label):
    cols = ", ".join(f"{f.name}:{f.type}" for f in tbl.schema)
    print(f"v{tbl.version}  {label}\nschema: {cols}")
    display(tbl.to_pandas())

show("start")

# %% [markdown]
# **Add column** ค่าเริ่มต้นเขียนเป็น SQL expression
# `credits` ค่าคงที่ `"0"` → Lance เดาเป็น int64 · `name_upper` คำนวณจาก column เดิม `upper(name)`
# schema บรรทัดบนตารางต้องมี 5 column แล้ว version 1 → 2

# %%
tbl.add_columns({"credits": "0", "name_upper": "upper(name)"})
show("add_columns credits, name_upper")

# %% [markdown]
# **Rename** ผ่าน `alter_columns` ระบุ `path` เดิม กับ `rename` ใหม่
# ไฟล์ data ไม่ถูกเขียนใหม่ เปลี่ยนแค่ใน manifest
# ดู schema: `plan` หาย `tier` มาแทน ค่าในตารางเดิมเป๊ะ

# %%
tbl.alter_columns({"path": "plan", "rename": "tier"})
show("rename plan -> tier")

# %% [markdown]
# **Change type** `alter_columns` รับ `data_type` ก็จริง
# แต่ cast ข้ามตระกูล int → float Lance 0.38 ปฏิเสธ
# ลองดูก่อน อ่าน error ให้ครบ ตารางข้างล่างเก็บคำขอกับคำตอบไว้คู่กัน

# %%
import pyarrow as pa
try:
    tbl.alter_columns({"path": "credits", "data_type": pa.float64()})
    result = "ok"
except ValueError as e:
    result = f"refused: {e}"
pd.set_option("display.max_colwidth", 120)
pd.DataFrame({"": ["request", "result"], "value": ["alter_columns credits int64 -> float64", result]}).set_index("")

# %% [markdown]
# วิธีที่ใช้ได้จริง สามขั้น แต่ละขั้นหนึ่ง version
# 1. add `credits_f` = `CAST(credits AS DOUBLE)` (v3 → v4)
# 2. drop `credits` เดิม (v4 → v5)
# 3. rename `credits_f` → `credits` (v5 → v6)
# ผลลัพธ์: ชื่อเดิม type ใหม่ `credits:double` ค่า 0 → 0.0 ทุกขั้นย้อนได้

# %%
tbl.add_columns({"credits_f": "CAST(credits AS DOUBLE)"})
tbl.drop_columns(["credits"])
tbl.alter_columns({"path": "credits_f", "rename": "credits"})
show("credits int64 -> float64 in 3 steps")

# %% [markdown]
# **Drop column** ลบออกจาก schema
# ข้อมูลใน fragment เดิมยังอยู่ แค่ manifest ไม่ชี้ไปหาอีก
# `name_upper` หายจาก schema version 6 → 7

# %%
tbl.drop_columns(["name_upper"])
show("drop name_upper")

# %% [markdown]
# **ดูประวัติ** ทุก version มี timestamp และรู้ว่าตัวเองใช้ data file กี่ไฟล์ กี่ byte
# manifest แต่ละอันคือ snapshot ของ schema + fragment ที่ใช้อยู่ตอนนั้น
# สังเกต bytes ขึ้นตอน add column (เขียนไฟล์ column ใหม่) และลงตอน drop (ไม่ชี้ไปหาไฟล์นั้นแล้ว)

# %%
steps = ["create", "add_columns", "rename plan->tier", "add credits_f", "drop credits", "rename credits_f->credits", "drop name_upper"]
pd.DataFrame([{"version": v["version"], "what": steps[i] if i < len(steps) else "",
               "data files": int(v["metadata"]["total_data_files"]), "bytes": int(v["metadata"]["total_files_size"])}
              for i, v in enumerate(tbl.list_versions())])

# %% [markdown]
# **ย้อนดู** `checkout(1)` เปิด version 1 แบบอ่านอย่างเดียว
# เห็น schema แรกสุด 3 column `plan` ยังอยู่ `credits` ยังไม่มี

# %%
tbl.checkout(1)
show("checkout 1 (read-only)")

# %% [markdown]
# **Restore** ทำให้ version ที่ checkout อยู่ กลายเป็น version ล่าสุด
# ไม่ได้ลบ version กลางทาง แค่สร้าง version 8 ที่หน้าตาเหมือน version 1
# ตารางท้ายสุดยืนยัน: version 1–8 อยู่ครบ Nothing is Deleted

# %%
tbl.restore()
show("after restore")
vs = [v["version"] for v in tbl.list_versions()]
pd.DataFrame([["✓"] * len(vs)], columns=[f"v{v}" for v in vs], index=["still on disk"])
