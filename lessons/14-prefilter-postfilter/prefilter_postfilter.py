# %% [markdown]
# # Lesson 14 — prefilter vs postfilter · กรองก่อนหรือกรองหลัง
#
# `where` กับ vector search ทำงานร่วมกันได้สองแบบ
# **prefilter** กรองแถวด้วย `where` ก่อน แล้วค่อยหา nearest ในกลุ่มที่เหลือ
# **postfilter** หา top-k จากทุกแถวก่อน แล้วค่อยกรอง ถ้า top-k ไม่มีแถวที่ตรง `where` ก็ได้ศูนย์
#
# ข้อมูลคือโพสต์จริงของ Nat 11 โพสต์ สามหัวข้อ `memory` `agents` `hardware`
# vector 3 มิติทำมือ แกนคือ `[memory, agents, hardware]`

# %%
# %pip install -q lancedb pandas

# %%
import sys, urllib.request, pathlib
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import lancedb
db = lancedb.connect("./data")
tbl = db.create_table("posts", data=load("nat_posts.jsonl"), mode="overwrite")
tbl.to_pandas()[["id", "date", "topic", "vector", "text"]].assign(text=lambda d: d.text.str[:40])

# %% [markdown]
# คำถาม "โพสต์เรื่อง **hardware** ที่ใกล้เรื่อง memory ที่สุด 2 โพสต์"
# ทิศ memory คือ `[1, 0, 0]`
# ไม่มี `where` ก่อน top-2 คือ p02 p01 ทั้งคู่เป็น memory (p01 กับ p04 ห่างเท่ากัน 0.02 เลือกตัวแรก)

# %%
q = [1.0, 0.0, 0.0]
tbl.search(q).limit(2).to_pandas()[["id", "topic", "_distance", "text"]].assign(text=lambda d: d.text.str[:40])

# %% [markdown]
# **prefilter** — กรองเหลือ hardware 3 โพสต์ก่อน แล้วค่อยวัดระยะ
# ได้ p09 p10 โพสต์จอกับเฟิร์มแวร์ ใกล้ memory ที่สุดในกลุ่ม hardware

# %%
tbl.search(q).where("topic = 'hardware'", prefilter=True).limit(2).to_pandas()[["id", "topic", "_distance", "text"]].assign(text=lambda d: d.text.str[:40])

# %% [markdown]
# **postfilter** — เอา top-2 จากทุกโพสต์ (p02 p01) แล้วค่อยกรองเหลือ hardware
# ไม่เหลือสักแถว ตารางว่าง ทั้งที่โพสต์ hardware มีอยู่ 3 โพสต์

# %%
tbl.search(q).where("topic = 'hardware'", prefilter=False).limit(2).to_pandas()[["id", "topic", "_distance", "text"]]

# %% [markdown]
# postfilter จะเห็น hardware ก็ต่อเมื่อ `limit` ใหญ่พอให้หลุดเข้า top-k
# `limit(11)` = ทุกโพสต์ ค่อยได้ครบสาม
#
# ทำไมถึงมี postfilter ให้เลือก
# กับ index (บทที่ 11) prefilter ต้องกรองก่อนเดินเข้า index บางกรณีช้ากว่า
# postfilter เร็วกว่าแต่เสี่ยงหาย สำหรับความจำ agent ที่กรองด้วย session หรือ agent id ใช้ prefilter

# %%
tbl.search(q).where("topic = 'hardware'", prefilter=False).limit(11).to_pandas()[["id", "topic", "_distance", "text"]].assign(text=lambda d: d.text.str[:40])
