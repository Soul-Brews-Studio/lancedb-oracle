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
# `Vector(3)` ประกาศครั้งเดียว ได้ `fixed_size_list<float>[3]` เหมือนบทที่แล้ว
# ต่างกันตรงที่คราวนี้ความยาวเขียนอยู่ในโค้ด ไม่ได้เดาจากแถวแรก

# %%
import lancedb
from lancedb.pydantic import LanceModel, Vector


class Point(LanceModel):
    id: str
    vector: Vector(3)


db = lancedb.connect("./data")
tbl = db.create_table("points", schema=Point, mode="overwrite")
tbl.schema

# %% [markdown]
# ส่ง `Point(...)` เข้าไปตรง ๆ ไม่ต้องแปลงเป็น dict

# %%
tbl.add([
    Point(id="a", vector=[1.0, 0.0, 0.0]),
    Point(id="b", vector=[0.0, 1.0, 0.0]),
    Point(id="d", vector=[0.9, 0.1, 0.0]),
])
tbl.count_rows()

# %% [markdown]
# `to_pydantic(Point)` คืน list ของ `Point` ไม่ใช่ DataFrame
# เข้าถึง field ด้วย `p.id` `p.vector` แบบ object ปกติ

# %%
hits = tbl.search([1.0, 0.0, 0.0]).limit(2).to_pydantic(Point)
for p in hits:
    print(p.id, list(p.vector))

# %% [markdown]
# ใส่ vector ยาว 2 ให้ field ที่ประกาศไว้ 3
# Pydantic โยน `ValidationError` ตั้งแต่ตอนสร้าง object
# ยังไม่ทันแตะ LanceDB ด้วยซ้ำ

# %%
try:
    Point(id="bad", vector=[1.0, 0.0])
except Exception as e:
    print(type(e).__name__, "-", str(e).splitlines()[0])
