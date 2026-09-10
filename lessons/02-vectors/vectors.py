# %% [markdown]
# # Lesson 2 — vectors · เวกเตอร์
#
# vector คือ list ของ float ยาวเท่ากันทุกแถว แค่นั้น
# ค้นหาด้วย vector ได้แถวกลับมาพร้อม column เพิ่มหนึ่งอัน `_distance`
# บทนี้ใช้ 3 มิติ 5 แถว เพื่อให้คิดตามด้วยมือได้

# %%
# %pip install -q lancedb pandas

# %%
import lancedb

db = lancedb.connect("./data")

# %% [markdown]
# column ชื่อ `vector` ใส่ list ของ float เข้าไป
# LanceDB ดูแถวแรกแล้วตัดสินว่าความยาว 3 ทุกแถวหลังจากนั้นต้อง 3 เท่ากัน
# ใน schema จะเห็นเป็น `fixed_size_list<float>[3]` — Arrow type ธรรมดา ไม่ใช่ของพิเศษ

# %%
rows = [
    {"id": "a", "vector": [1.0, 0.0, 0.0]},
    {"id": "b", "vector": [0.0, 1.0, 0.0]},
    {"id": "c", "vector": [0.0, 0.0, 1.0]},
    {"id": "d", "vector": [0.9, 0.1, 0.0]},  # close to a
    {"id": "e", "vector": [0.5, 0.5, 0.0]},  # between a and b
]
tbl = db.create_table("points", data=rows, mode="overwrite")
tbl.schema

# %%
tbl.to_pandas()

# %% [markdown]
# ถามว่าแถวไหนใกล้ `[1, 0, 0]` ที่สุด
# ยังไม่มี index เลยไล่วัดระยะทุกแถว (brute force) 5 แถวก็เร็ว
# แสนแถวก็ยังใช้โค้ดเดิม แค่ช้าลง ตรงนั้นแหละที่ index เข้ามาช่วย (บทที่ 4)
#
# `_distance` ค่า default คือ L2 ยกกำลังสอง คิดเองได้
# `d` = (1−0.9)² + (0−0.1)² + 0 = 0.02

# %%
q = [1.0, 0.0, 0.0]
tbl.search(q).limit(3).to_pandas()

# %% [markdown]
# เปลี่ยน metric เป็น cosine ดูทิศทางอย่างเดียว ไม่สนความยาว
# `e` ทำมุม 45° กับ `q` ก็ได้ 1 − cos 45° = 0.293
# ลำดับยังเหมือนเดิมในตัวอย่างนี้ แต่ถ้าคูณ vector ด้วย 10
# L2 จะเห็นว่าไกลออกไปมาก cosine ไม่ขยับเลย
#
# text embedding ส่วนใหญ่ normalize มาแล้ว repo ใน fleet เลยใช้ cosine กัน

# %%
tbl.search(q).metric("cosine").limit(3).to_pandas()
