# %% [markdown]
# # Lesson 7 — real embeddings · เทียบ vector ทำมือกับ vector จากโมเดล
#
# บทก่อนหน้า vector 3 มิติทำมือ `[memory, agents, hardware]` ตั้งใจให้คิดตามได้
# บทนี้ให้โมเดลอ่านข้อความแล้วสร้าง vector เอง 384 มิติ
# แล้วเทียบ โพสต์เดียวกัน 11 โพสต์ เพื่อนบ้านที่ใกล้ที่สุดตรงกันไหม
#
# โมเดล `paraphrase-multilingual-MiniLM-L12-v2` รู้ภาษาไทย โหลดครั้งแรก ~470 MB

# %%
# %pip install -q lancedb pandas sentence-transformers

# %%
import os, sys, urllib.request, pathlib, warnings
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TQDM_DISABLE"] = "1"
warnings.filterwarnings("ignore")
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry

posts = load("nat_posts.jsonl")
db = lancedb.connect("./data")

# %% [markdown]
# **ตารางที่ 1 — vector ทำมือ** เหมือนบทที่ 14 ตรง ๆ

# %%
hand = db.create_table("hand", data=posts, mode="overwrite")

# %% [markdown]
# **ตารางที่ 2 — vector จากโมเดล**
# `SourceField` บอกว่า column ไหนคือข้อความต้นทาง `VectorField` บอกว่า column ไหนให้โมเดลเติม
# ตอน `add` ส่งแค่ `text` เข้าไป vector โผล่มาเองไม่ต้องเขียน

# %%
model = get_registry().get("sentence-transformers").create(name="paraphrase-multilingual-MiniLM-L12-v2")

class Post(LanceModel):
    id: str
    date: str
    topic: str
    text: str = model.SourceField()
    vector: Vector(model.ndims()) = model.VectorField()

auto = db.create_table("auto", schema=Post, mode="overwrite")
auto.add([{k: p[k] for k in ("id", "date", "topic", "text")} for p in posts])
print(auto.schema.field("vector"))   # 384 dims, nobody typed them

# %% [markdown]
# **เทียบเพื่อนบ้าน** — ทุกโพสต์ ถามว่าใครใกล้ที่สุด (ไม่นับตัวเอง)
# ซ้ายคือคำตอบจาก vector ทำมือ ขวาคือจากโมเดล ตรงกันไหม หัวข้อเดียวกันไหม

# %%
import pandas as pd

def nearest(tbl, p, k=2):
    hits = tbl.search(p["vector"] if "vector" in p else p["text"]).limit(k + 1).to_list()
    return [h["id"] for h in hits if h["id"] != p["id"]][:k]

hand_rows = {r["id"]: r for r in hand.to_pandas().to_dict("records")}
topic = {p["id"]: p["topic"] for p in posts}
rows = []
for p in posts:
    h = nearest(hand, hand_rows[p["id"]], 1)[0]
    a = nearest(auto, {"id": p["id"], "text": p["text"]}, 1)[0]
    rows.append({"post": p["id"], "topic": p["topic"], "hand→": h, "auto→": a,
                 "same?": "✓" if h == a else "", "auto same topic?": "✓" if topic[a] == p["topic"] else "✗"})
pd.DataFrame(rows)

# %% [markdown]
# **ถามด้วยข้อความ** — vector ทำมือทำแบบนี้ไม่ได้ ต้องแปลงคำถามเป็นตัวเลขเอง
# ตาราง `auto` รับ string ตรง ๆ โมเดล embed คำถามให้ แล้วค่อยวัดระยะ

# %%
for q in ["สร้าง memory ให้ AI", "ต่อจอกับ ESP32", "agent หลายตัวคุยกัน"]:
    hits = auto.search(q).limit(2).to_pandas()
    print(f"\nQ: {q}")
    for _, h in hits.iterrows():
        print(f"   {h['id']} {h['topic']:<9} {h['_distance']:.3f}  {h['text'][:45]}")

# %% [markdown]
# บน disk ตาราง `auto` ใหญ่กว่า `hand` เพราะ 384 float ต่อแถวแทน 3
# 11 แถวยังเล็กมาก แต่สัดส่วนนี้คงที่ ล้านแถวคือ 1.5 GB สำหรับ vector อย่างเดียว

# %%
from pathlib import Path
for name in ("hand", "auto"):
    size = sum(f.stat().st_size for f in Path(f"data/{name}.lance/data").glob("*.lance"))
    print(f"{name:<5} {size:>7} bytes")
