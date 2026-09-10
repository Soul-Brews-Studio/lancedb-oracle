# %% [markdown]
# # Lesson 14 — prefilter vs postfilter · กรองก่อนหรือกรองหลัง
#
# `where` กับ vector search ทำงานร่วมกันได้สองแบบ
# **prefilter** กรองแถวด้วย `where` ก่อน แล้วค่อยหา nearest ในกลุ่มที่เหลือ
# **postfilter** หา top-k จากทุกแถวก่อน แล้วค่อยกรอง ถ้า top-k ไม่มีแถวที่ตรง `where` ก็ได้ศูนย์
# 5 แถว 3 มิติ เห็นความต่างด้วยตา

# %%
# %pip install -q lancedb pandas

# %%
import lancedb

db = lancedb.connect("./data")

# %% [markdown]
# agent A สามแถว เกาะกลุ่มใกล้ `[1, 0, 0]`
# agent B สองแถว อยู่ไกลออกไป

# %%
tbl = db.create_table("memories", data=[
    {"id": "a1", "agent": "A", "vector": [1.0, 0.0, 0.0]},
    {"id": "a2", "agent": "A", "vector": [0.9, 0.1, 0.0]},
    {"id": "a3", "agent": "A", "vector": [0.8, 0.2, 0.0]},
    {"id": "b1", "agent": "B", "vector": [0.5, 0.5, 0.0]},
    {"id": "b2", "agent": "B", "vector": [0.0, 1.0, 0.0]},
], mode="overwrite")
tbl.to_pandas()

# %% [markdown]
# คำถาม "ความจำของ agent B ที่ใกล้ `[1, 0, 0]` ที่สุด 2 อัน"
# ไม่มี `where` ก่อน top-2 คือ a1 a2 ทั้งคู่เป็น A

# %%
q = [1.0, 0.0, 0.0]
tbl.search(q).limit(2).to_pandas()[["id", "agent", "_distance"]]

# %% [markdown]
# **prefilter** — กรองเหลือ B สองแถวก่อน แล้วค่อยวัดระยะ
# ได้ b1 b2 ครบ

# %%
tbl.search(q).where("agent = 'B'", prefilter=True).limit(2).to_pandas()[["id", "agent", "_distance"]]

# %% [markdown]
# **postfilter** — เอา top-2 จากทุกแถว (a1 a2) แล้วค่อยกรองเหลือ B
# ไม่เหลือสักแถว คำตอบว่างเปล่า ทั้งที่ b1 b2 มีอยู่จริง

# %%
tbl.search(q).where("agent = 'B'", prefilter=False).limit(2).to_pandas()[["id", "agent", "_distance"]]

# %% [markdown]
# postfilter จะเห็น B ก็ต่อเมื่อ `limit` ใหญ่พอให้ B หลุดเข้า top-k
# `limit(5)` = ทุกแถว ค่อยได้ b1 b2 กลับมา
#
# ทำไมถึงมี postfilter ให้เลือก
# กับ index (บทที่ 11) prefilter ต้องกรองก่อนเดินเข้า index บางกรณีช้ากว่า
# postfilter เร็วกว่าแต่เสี่ยงหาย ต้องเลือกเอง

# %%
tbl.search(q).where("agent = 'B'", prefilter=False).limit(5).to_pandas()[["id", "agent", "_distance"]]
