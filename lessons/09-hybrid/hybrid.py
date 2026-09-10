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
# helper เดียว ยิงสามแบบด้วยคำถามเดียวกัน ได้ตารางเดียว แถวละอันดับ (1 2 3)
# แต่ละวิธีมีสองคอลัมน์ id กับข้อความ แล้วตามด้วยคะแนนของวิธีนั้น
# vector ใช้ `_distance` (ต่ำ = ดี) · fts ใช้ `_score` (สูง = ดี) · hybrid ใช้ `_relevance_score` (สูง = ดี)

# %%
import pandas as pd
from IPython.display import display

snippet = {p["id"]: p["text"][:24] for p in load("nat_posts.jsonl")}

def three_ways(q, k=3):
    v = tbl.search(q, query_type="vector").limit(k).to_list()
    f = tbl.search(q, query_type="fts").limit(k).to_list()
    h = tbl.search(q, query_type="hybrid").rerank(reranker=RRFReranker()).limit(k).to_list()
    rows = []
    for rank in range(k):
        r = {"rank": rank + 1}
        for name, hits, key, nd in (("vector", v, "_distance", 2), ("fts", f, "_score", 2), ("hybrid", h, "_relevance_score", 4)):
            hit = hits[rank] if rank < len(hits) else None
            r[f"{name} id"] = hit["id"] if hit else "—"
            r[f"{name} text"] = snippet[hit["id"]] if hit else ""
            r[f"{name} {key}"] = round(hit[key], nd) if hit else None
        rows.append(r)
    df = pd.DataFrame(rows).set_index("rank")
    df.columns = pd.MultiIndex.from_tuples([(c.split(" ", 1)[0], c.split(" ", 1)[1]) for c in df.columns])
    return df

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
# แต่ละฝั่งให้ 1/(60 + อันดับ) แล้วบวกกัน ฝั่งไหนไม่มีโพสต์นั้น ให้ 0
#
# ตารางข้างล่างคำนวณเองทีละขั้น แล้วเทียบกับ `_relevance_score` ที่ LanceDB คืนมา
# อ่านแถวแรกของ "ความทรงจำ": p03 อันดับ 2 ฝั่ง vector = 1/62 = 0.0161 · อันดับ 1 ฝั่ง fts = 1/61 = 0.0164
# บวกกัน 0.0325 ตรงกับ LanceDB ทศนิยมสี่ตำแหน่ง คอลัมน์ `match` ขึ้น ✓
# p01 p04 มีแค่ฝั่ง vector fts ให้ 0 เลยตกมาอยู่อันดับ 2 3 ด้วยคะแนนแค่ครึ่งเดียว
#
# ไม่มีโมเดลเพิ่ม ไม่มี GPU reranker แบบอื่น (cross-encoder) ต้องโหลดโมเดลอีกตัว

# %%
K = 60

def rrf_breakdown(q, k=3):
    v = [x["id"] for x in tbl.search(q, query_type="vector").limit(k).to_list()]
    f = [x["id"] for x in tbl.search(q, query_type="fts").limit(k).to_list()]
    lance = {x["id"]: x["_relevance_score"]
             for x in tbl.search(q, query_type="hybrid").rerank(reranker=RRFReranker()).limit(k).to_list()}
    rows = []
    for pid in dict.fromkeys(v + f):
        vr = v.index(pid) + 1 if pid in v else None
        fr = f.index(pid) + 1 if pid in f else None
        pv = 1 / (K + vr) if vr else 0.0
        pf = 1 / (K + fr) if fr else 0.0
        rows.append({
            "id": pid, "text": snippet[pid],
            "vector rank": vr or "—", "fts rank": fr or "—",
            f"1/({K}+vr)": round(pv, 4), f"1/({K}+fr)": round(pf, 4),
            "rrf sum": round(pv + pf, 4),
            "lancedb _relevance_score": round(lance[pid], 4) if pid in lance else None,
            "match": "✓" if pid in lance and abs(lance[pid] - (pv + pf)) < 1e-4 else "",
        })
    df = pd.DataFrame(rows).sort_values("rrf sum", ascending=False).reset_index(drop=True)
    df.insert(0, "question", [q] + [""] * (len(df) - 1))
    return df

for q in ["ความทรงจำ", "Messenger"]:
    display(rrf_breakdown(q))
