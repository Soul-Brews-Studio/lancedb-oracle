# %% [markdown]
# # Lesson 2 — vectors · เวกเตอร์
#
# vector คือ list ของ float ยาวเท่ากันทุกแถว แค่นั้น
# ค้นหาด้วย vector ได้แถวกลับมาพร้อม column เพิ่มหนึ่งอัน `_distance`
# บทนี้ใช้ 3 มิติ 5 แถว ทุกตัวเลขคิดตามด้วยมือได้ และมีตารางเช็คคำตอบให้ทุกครั้ง

# %%
# %pip install -q lancedb pandas

# %%
import lancedb
import pandas as pd

db = lancedb.connect("./data")

# %% [markdown]
# column ชื่อ `vector` ใส่ list ของ float เข้าไป
# LanceDB ดูแถวแรกแล้วตัดสินว่าความยาว 3 ทุกแถวหลังจากนั้นต้อง 3 เท่ากัน
# ใน schema เห็นเป็น `fixed_size_list<item: float>[3]` — Arrow type ธรรมดา ไม่ใช่ของพิเศษ

# %%
rows = [
    {"id": "a", "vector": [1.0, 0.0, 0.0]},
    {"id": "b", "vector": [0.0, 1.0, 0.0]},
    {"id": "c", "vector": [0.0, 0.0, 1.0]},
    {"id": "d", "vector": [0.9, 0.1, 0.0]},  # close to a
    {"id": "e", "vector": [0.5, 0.5, 0.0]},  # between a and b
]
tbl = db.create_table("points", data=rows, mode="overwrite")
pd.DataFrame([{"column": f.name, "arrow type": str(f.type)} for f in tbl.schema])

# %%
tbl.to_pandas()

# %% [markdown]
# **คำถาม** แถวไหนใกล้ `q = [1, 0, 0]` ที่สุด
# ยังไม่มี index เลยไล่วัดระยะทุกแถว (brute force) 5 แถวก็เร็ว
# แสนแถวก็ยังใช้โค้ดเดิม แค่ช้าลง ตรงนั้นแหละที่ index เข้ามาช่วย (บทที่ 11)
#
# `_distance` ค่า default คือ **L2 ยกกำลังสอง** = ผลต่างแต่ละแกนยกกำลังสอง แล้วบวกกัน
# ดูแถว `d`: (1−0.9)² + (0−0.1)² + (0−0)² = 0.01 + 0.01 + 0 = **0.02**

# %%
q = [1.0, 0.0, 0.0]
tbl.search(q).limit(3).to_pandas()

# %% [markdown]
# **เช็คด้วยมือ** ทุกแถว ไม่ใช่แค่ 3 อันดับแรก
# คอลัมน์ `dx²` `dy²` `dz²` คือผลต่างยกกำลังสองแต่ละแกน `sum` คือผลรวม
# `_distance` คือคำตอบจาก LanceDB `match` ต้องเป็น True ทุกแถว

# %%
def l2_by_hand(v, q):
    d = [(vi - qi) ** 2 for vi, qi in zip(v, q)]
    return {"dx²": round(d[0], 4), "dy²": round(d[1], 4), "dz²": round(d[2], 4), "sum": round(sum(d), 4)}

lance = {h["id"]: h["_distance"] for h in tbl.search(q).limit(5).to_list()}
check = []
for r in rows:
    hand = l2_by_hand(r["vector"], q)
    check.append({"id": r["id"], "vector": r["vector"], **hand,
                  "_distance": round(lance[r["id"]], 4), "match": abs(hand["sum"] - lance[r["id"]]) < 1e-6})
pd.DataFrame(check).sort_values("_distance")

# %% [markdown]
# **cosine** ดูทิศทางอย่างเดียว ไม่สนความยาว
# สูตร: `_distance = 1 − (v·q) / (|v| |q|)`
# ดูแถว `e`: v·q = 0.5 · |v| = √0.5 = 0.7071 · |q| = 1 → 1 − 0.5/0.7071 = **0.2929**
# ลำดับยังเหมือน L2 ในตัวอย่างนี้ แต่ตัวเลขคนละสเกล

# %%
tbl.search(q).metric("cosine").limit(3).to_pandas()

# %% [markdown]
# เช็คด้วยมืออีกรอบ `dot` = v·q · `|v|` = ความยาวของ v · `1-cos` = คำตอบที่ควรได้
# `match` ต้อง True ทุกแถว (ต่างกันได้ที่ทศนิยมตำแหน่งที่ 6 เพราะ float32)

# %%
import math

lance_cos = {h["id"]: h["_distance"] for h in tbl.search(q).metric("cosine").limit(5).to_list()}
check = []
for r in rows:
    v = r["vector"]
    dot = sum(vi * qi for vi, qi in zip(v, q))
    nv, nq = math.sqrt(sum(x * x for x in v)), math.sqrt(sum(x * x for x in q))
    hand = 1 - dot / (nv * nq)
    check.append({"id": r["id"], "vector": v, "dot": round(dot, 4), "|v|": round(nv, 4), "|q|": nq,
                  "1-cos": round(hand, 4), "_distance": round(lance_cos[r["id"]], 4),
                  "match": abs(hand - lance_cos[r["id"]]) < 1e-5})
pd.DataFrame(check).sort_values("_distance")

# %% [markdown]
# **ทำไมต้องมีสองแบบ** คูณ `d` ด้วย 10 เป็น `[9, 1, 0]` ทิศเดิม ยาวขึ้น
# L2 บอกว่าไกลมาก (8² + 1² = 65) cosine บอกว่าเท่าเดิมเป๊ะ (0.0061)
# text embedding ส่วนใหญ่ normalize ความยาวมาแล้ว repo ใน fleet เลยใช้ cosine กัน

# %%
big = db.create_table("scaled", data=[{"id": "d", "vector": [0.9, 0.1, 0.0]}, {"id": "d×10", "vector": [9.0, 1.0, 0.0]}], mode="overwrite")
l2 = big.search(q).limit(2).to_pandas()[["id", "_distance"]].rename(columns={"_distance": "L2²"})
cs = big.search(q).metric("cosine").limit(2).to_pandas()[["id", "_distance"]].rename(columns={"_distance": "cosine"})
l2.merge(cs, on="id").round(4)
