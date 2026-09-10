# %% [markdown]
# # Lesson 3 — ORM style · ประกาศตารางเป็น class
#
# บทที่แล้วส่ง dict เข้าไปให้เดา schema
# บทนี้ประกาศ schema เป็น Pydantic class แทน
# แถวเข้าเป็น object แถวออกเป็น object ผิด shape โดนดักก่อนถึง disk

# %%
# %pip install -q lancedb pandas

# %% [markdown]
# `LanceModel` คือ Pydantic `BaseModel` ที่รู้จัก Arrow
# `Vector(3)` ประกาศครั้งเดียว ได้ `fixed_size_list<item: float>[3]` เหมือนบทที่แล้ว
# ต่างกันตรงที่คราวนี้ความยาวเขียนอยู่ในโค้ด ไม่ได้เดาจากแถวแรก
# ตาราง schema ข้างล่างต้องเหมือนบทที่ 2 ทุกตัวอักษร

# %%
import lancedb
import pandas as pd
from lancedb.pydantic import LanceModel, Vector


class Point(LanceModel):
    id: str
    vector: Vector(3)


db = lancedb.connect("./data")
tbl = db.create_table("points", schema=Point, mode="overwrite")
pd.DataFrame([{"column": f.name, "arrow type": str(f.type)} for f in tbl.schema])

# %% [markdown]
# ส่ง `Point(...)` เข้าไปตรง ๆ ไม่ต้องแปลงเป็น dict
# ตารางเปล่าตอนสร้าง (rows 0) เพิ่มสาม object แล้วได้ rows 3

# %%
before = tbl.count_rows()
tbl.add([
    Point(id="a", vector=[1.0, 0.0, 0.0]),
    Point(id="b", vector=[0.0, 1.0, 0.0]),
    Point(id="d", vector=[0.9, 0.1, 0.0]),
])
pd.DataFrame([{"step": "after create_table", "rows": before}, {"step": "after add 3 Points", "rows": tbl.count_rows()}])

# %% [markdown]
# `to_pydantic(Point)` คืน list ของ `Point` ไม่ใช่ DataFrame
# เข้าถึง field ด้วย `p.id` `p.vector` แบบ object ปกติ
# ตารางข้างล่างสร้างจาก object ทีละตัว คอลัมน์ `python type` ยืนยันว่าได้ `Point` จริง
# ใกล้ `[1, 0, 0]` ที่สุดคือ a (0.0) แล้ว d (0.02) เหมือนบทที่ 2

# %%
hits = tbl.search([1.0, 0.0, 0.0]).limit(2).to_pydantic(Point)
pd.DataFrame([{"python type": type(p).__name__, "p.id": p.id, "p.vector": [round(x, 2) for x in p.vector]} for p in hits])

# %% [markdown]
# ใส่ vector ยาว 2 ให้ field ที่ประกาศไว้ 3
# Pydantic โยน `ValidationError` ตั้งแต่ตอนสร้าง object ยังไม่ทันแตะ LanceDB
# แถวแรกในตารางคือของถูก แถวสองคือของผิด ดูคอลัมน์ `result`

# %%
attempts = []
for vec in ([1.0, 0.0, 0.0], [1.0, 0.0]):
    try:
        Point(id="x", vector=vec)
        attempts.append({"vector": vec, "length": len(vec), "result": "ok — Point created"})
    except Exception as e:
        attempts.append({"vector": vec, "length": len(vec), "result": f"{type(e).__name__}: {str(e).splitlines()[0]}"})
pd.DataFrame(attempts)
