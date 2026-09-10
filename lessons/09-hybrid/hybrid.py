# %% [markdown]
# # Lesson 9 — hybrid search · vector + FTS รวมกัน
#
# บทที่ 7 vector ตอบ "ความหมายใกล้" บทที่ 8 FTS ตอบ "มีคำนี้จริง"
# แต่ละอันพลาดคนละแบบ hybrid ยิงทั้งสองพร้อมกัน แล้วให้ reranker รวมอันดับ
# คะแนนใหม่ชื่อ `_relevance_score` ไม่ใช่ `_distance` ไม่ใช่ `_score`
# โพสต์ 11 โพสต์เดิม โมเดลเดิม tokenizer `icu` เดิม

# %%
# %pip install -q lancedb pandas sentence-transformers

# %%
import os, sys, urllib.request, pathlib, warnings
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"; os.environ["TQDM_DISABLE"] = "1"
warnings.filterwarnings("ignore")
if not pathlib.Path("../data/lesson_data.py").exists():
    urllib.request.urlretrieve("https://raw.githubusercontent.com/Soul-Brews-Studio/lancedb-oracle/main/lessons/data/lesson_data.py", "lesson_data.py")
sys.path.insert(0, "../data")
from lesson_data import load

import lancedb
from lancedb.pydantic import LanceModel, Vector
from lancedb.embeddings import get_registry
from lancedb.index import FTS
from lancedb.rerankers import RRFReranker

model = get_registry().get("sentence-transformers").create(name="paraphrase-multilingual-MiniLM-L12-v2")

class Post(LanceModel):
    id: str
    topic: str
    text: str = model.SourceField()
    vector: Vector(model.ndims()) = model.VectorField()

db = lancedb.connect("./data")
tbl = db.create_table("posts", schema=Post, mode="overwrite")
tbl.add([{k: p[k] for k in ("id", "topic", "text")} for p in load("nat_posts.jsonl")])
tbl.create_index("text", config=FTS(base_tokenizer="icu"))

# %% [markdown]
# helper เดียว ยิงสามแบบด้วยคำถามเดียวกัน วาง 3 คอลัมน์เทียบกัน
# vector ใช้ `_distance` (ต่ำ = ดี) · fts ใช้ `_score` (สูง = ดี) · hybrid ใช้ `_relevance_score` (สูง = ดี)

# %%
import pandas as pd

def three_ways(q, k=3):
    v = tbl.search(q, query_type="vector").limit(k).to_list()
    f = tbl.search(q, query_type="fts").limit(k).to_list()
    h = tbl.search(q, query_type="hybrid").rerank(reranker=RRFReranker()).limit(k).to_list()
    pad = lambda xs, key, fmt: [f"{x['id']} {fmt(x[key])}" for x in xs] + [""] * (k - len(xs))
    return pd.DataFrame({
        "vector (_distance)": pad(v, "_distance", lambda d: f"{d:.2f}"),
        "fts (_score)": pad(f, "_score", lambda s: f"{s:.2f}"),
        "hybrid (_relevance_score)": pad(h, "_relevance_score", lambda s: f"{s:.3f}"),
    })

# %% [markdown]
# **คำถาม 1 — "จอ ESP32"**
# FTS เจอคำ "จอ" ใน p09 p10 และ "esp32" ใน URL ของ p11 ได้ hardware ครบสาม
# vector ปล่อย p05 (memory) หลุดเข้ามาอันดับสอง เพราะ "Visualize" กับ "จอ" ความหมายใกล้กัน
# hybrid เอาที่สองฝั่งเห็นตรงกัน (p10 p09) ขึ้นก่อน p11 ตามมา p05 ตกไป

# %%
three_ways("จอ ESP32")

# %% [markdown]
# **คำถาม 2 — "ความทรงจำ"**
# FTS เจอ p03 โพสต์เดียว ที่มีคำนี้ตรง ๆ แล้วหมด
# vector เจอ memory ทั้งกลุ่ม แม้ไม่มีคำว่า "ความทรงจำ" (ใช้คำว่า Memory แทน)
# hybrid เอา p03 ขึ้นก่อน เพราะสองฝั่งเห็นตรงกัน แล้วเติมที่เหลือจาก vector

# %%
three_ways("ความทรงจำ")

# %% [markdown]
# **คำถาม 3 — "Messenger"**
# คำเดียว โพสต์เดียว (p06) FTS แม่นสุด vector เดาไปทาง agents
# hybrid ยังคง p06 อันดับหนึ่ง

# %%
three_ways("Messenger")

# %% [markdown]
# **RRF ทำงานยังไง** — Reciprocal Rank Fusion ไม่สนคะแนนดิบ สนแค่อันดับ
# แต่ละฝั่งให้ 1/(60 + อันดับ) แล้วบวกกัน
# "ความทรงจำ": p03 อันดับ 1 ใน FTS อันดับ 2 ใน vector = 1/61 + 1/62 = 0.0325 ตรงกับ `_relevance_score` ข้างบน
# "Messenger": p06 อันดับ 1 ทั้งสองฝั่ง = 1/61 + 1/61 = 0.0328
# ฝั่งที่ไม่มี p ตัวนั้นในลิสต์ ให้ 0 เลยตกอันดับเอง
#
# ไม่มีโมเดลเพิ่ม ไม่มี GPU reranker แบบอื่น (cross-encoder) ต้องโหลดโมเดลอีกตัว

# %%
for q in ["ความทรงจำ", "Messenger"]:
    v = [x["id"] for x in tbl.search(q, query_type="vector").limit(3).to_list()]
    f = [x["id"] for x in tbl.search(q, query_type="fts").limit(3).to_list()]
    ids = dict.fromkeys(v + f)
    rrf = {i: (1 / (60 + v.index(i) + 1) if i in v else 0) + (1 / (60 + f.index(i) + 1) if i in f else 0) for i in ids}
    top = sorted(rrf.items(), key=lambda kv: -kv[1])[:3]
    print(q, "->", [(i, round(s, 4)) for i, s in top])
