# %% [markdown]
# # Lesson 11 — IVF_PQ index · เมื่อ brute force ไม่พอ
#
# ทุกบทที่ผ่านมา 11 แถว ค้นทั้งตารางก็เร็ว
# บทนี้เป็นบทแรกที่ตั้งใจให้ข้อมูลโต 50,000 แถว 64 มิติ เพราะ index ต้องมีข้อมูลพอให้ train
# ยังเป็นตัวเลขสุ่ม ไม่ใช่โพสต์จริง เพราะเรื่องที่ดูคือเวลากับ recall ไม่ใช่ความหมาย
# สุ่มแบบเป็นกอ 100 กอ + noise เลียนแบบ embedding จริงที่เกาะกลุ่มตามหัวข้อ
# (สุ่มกระจายเท่ากันทั้ง space คือกรณีแย่สุดของ PQ recall ตกเหลือ 0.1–0.4 ลองได้)
#
# IVF = แบ่ง vector เป็น partition ค้นแค่บาง partition · PQ = บีบ vector ให้เล็กลง
# แลกความแม่นกับความเร็ว วัดทั้งสองอย่างให้เห็น

# %%
# %pip install -q lancedb pandas numpy

# %%
import time
import numpy as np
import pandas as pd
import lancedb
from lancedb.index import IvfPq

N, DIM, BLOBS = 50_000, 64, 100
rng = np.random.default_rng(0)
centers = rng.random((BLOBS, DIM), dtype=np.float32)
vecs = (centers[rng.integers(0, BLOBS, N)] + rng.normal(0, 0.1, (N, DIM))).astype(np.float32)

db = lancedb.connect("./data")
tbl = db.create_table("points", data=[{"id": i, "vector": vecs[i]} for i in range(N)], mode="overwrite")
q = vecs[42]
print(tbl.count_rows(), "rows,", DIM, "dims")

# %% [markdown]
# **brute force** — ยังไม่มี index วัดระยะทุกแถว
# คำตอบชุดนี้คือความจริง ใช้เทียบกับ index ทีหลัง
# query คือแถว 42 เอง อันดับ 1 ต้องเป็น id 42 ระยะ 0.00 ที่เหลือคือเพื่อนในกอเดียวกัน

# %%
def timed(fn, n=5):
    fn()
    t0 = time.perf_counter()
    for _ in range(n):
        out = fn()
    return out, (time.perf_counter() - t0) / n * 1000

truth_hits, ms_brute = timed(lambda: tbl.search(q).limit(10).to_list())
truth = [h["id"] for h in truth_hits]
print(f"brute force over {N} rows: {ms_brute:.2f} ms per query")
pd.DataFrame([{"rank": i + 1, "id": h["id"], "_distance": round(h["_distance"], 3)} for i, h in enumerate(truth_hits)])

# %% [markdown]
# **สร้าง IVF_PQ** — `create_index("vector", config=IvfPq(...))` รูปแบบเดียวกับ FTS ในบทที่ 8
# แบบเก่า `create_index(metric=, num_partitions=)` ยังใช้ได้ แต่ `config=` คือทางที่เอกสาร 0.38 ชี้
# `num_partitions` จำนวนกลุ่ม กฎหยาบ ๆ คือ √N ≈ 224 ใช้ 200 · `num_sub_vectors` แบ่ง 64 มิติเป็น 8 ชิ้น ชิ้นละ 8
# train ใช้เวลาไม่กี่วินาที กับ 50k แถว

# %%
t0 = time.perf_counter()
tbl.create_index("vector", config=IvfPq(distance_type="l2", num_partitions=200, num_sub_vectors=8))
build_s = time.perf_counter() - t0
pd.DataFrame([{"index": i.name, "type": i.index_type, "columns": ", ".join(i.columns), "build seconds": round(build_s, 1)}
              for i in tbl.list_indices()])

# %% [markdown]
# **ค้นด้วย index** — `nprobes` คือจำนวน partition ที่ยอมเปิดดู จาก 200
# recall@10 = ใน 10 คำตอบจาก index มีกี่อันตรงกับ brute force
#
# ข้อมูลเป็นกอชัด query ตกในกอของตัวเองตั้งแต่ probe แรก เพิ่ม nprobes เลยช่วยได้นิดเดียว recall ค้างต่ำราว 0.1–0.5
# ดูคอลัมน์ `hits in true top-10` ตรง ๆ จาก 10 คำตอบ index เจอของจริงกี่อัน
# ตัวที่จำกัดคือ PQ ต่างหาก บีบ 64 float เหลือ 8 byte ระยะในกอเดียวกันแยกไม่ออก
# ตัวเลขขยับได้ทุกครั้งที่รัน เพราะ train index สุ่มจุดเริ่ม k-means ดูแนวโน้ม ไม่ต้องดูทศนิยม
# ที่ 50k แถว brute force ยังแค่ 4 ms index ยังไม่ได้เปรียบเรื่องเวลา บทนี้ดูกลไก ไม่ใช่ benchmark

# %%
def run(nprobes, refine_factor=None):
    def go():
        s = tbl.search(q).nprobes(nprobes).limit(10)
        if refine_factor:
            s = s.refine_factor(refine_factor)
        return [h["id"] for h in s.to_list()]
    ids, ms = timed(go)
    hit = len(set(ids) & set(truth))
    return {"nprobes": nprobes, "refine_factor": refine_factor or "—", "ms per query": round(ms, 2),
            "hits in true top-10": hit, "recall@10": hit / 10}, ids

results, found = [], {}
for nprobes in (1, 10, 50):
    row, ids = run(nprobes)
    results.append(row); found[nprobes] = ids
pd.DataFrame(results)

# %% [markdown]
# **ดูทีละ id** — brute force กับ index ที่ `nprobes=10` วางคู่กัน
# คอลัมน์ `same position?` ✓ = อันดับนั้น id ตรงกัน · `in true top-10?` ✓ = id จาก index อยู่ในคำตอบจริงที่ไหนสักแห่ง
# อันดับ 1 (id 42) index ยังหาเจอ ที่พลาดคืออันดับถัด ๆ ไป เพราะ PQ วัดระยะหยาบ

# %%
idx_ids = found[10]
pd.DataFrame([{
    "rank": i + 1,
    "brute force id": truth[i],
    "index id": idx_ids[i] if i < len(idx_ids) else "—",
    "same position?": "✓" if i < len(idx_ids) and idx_ids[i] == truth[i] else "",
    "in true top-10?": "✓" if i < len(idx_ids) and idx_ids[i] in truth else "✗",
} for i in range(10)])

# %% [markdown]
# **`refine_factor`** — ดึงมาเผื่อ k×factor แล้ววัดระยะจริง (ไม่ใช่ PQ) ค่อยตัดเหลือ k
# แก้ความหยาบของ PQ ตรงจุด recall กระโดดขึ้นไป 0.7–1.0 โดยเปิด partition เท่าเดิม
# ค่าที่ควรตั้งในระบบจริง `nprobes` ต่ำ + `refine_factor` 5–10

# %%
row_no, _ = run(10)
row_rf, _ = run(10, 5)
pd.DataFrame([row_no, row_rf])

# %% [markdown]
# บน disk index อยู่ใน `_indices/` เทียบกับ data
# 50k × 64 float32 = 12.8 MB ดิบ · PQ บีบเหลือ 8 byte ต่อ vector = 400 KB + centroid + row id
# นี่คือเหตุผลที่ล้านแถวยังค้นได้ในหน่วย ms

# %%
from pathlib import Path
root = Path("data/points.lance")
data = sum(f.stat().st_size for f in (root / "data").glob("*.lance"))
idx = sum(f.stat().st_size for f in (root / "_indices").rglob("*") if f.is_file())
pd.DataFrame([
    {"what": "data (50k × 64 float32)", "bytes": data, "bytes per vector": round(data / N, 1)},
    {"what": "IVF_PQ index", "bytes": idx, "bytes per vector": round(idx / N, 1)},
])
