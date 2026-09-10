# %% [markdown]
# # Lesson 13 — multi-table memory · ความจำสามชั้นของ agent
#
# ความจำของ agent ไม่ใช่ตารางเดียว แยกตามชนิด
# **episodic** เกิดอะไรขึ้น เมื่อไหร่ · **semantic** รู้อะไร · **procedural** ทำยังไง
# บทนี้สร้างสามตารางเล็ก ๆ ค้นด้วย vector เดียวกันทั้งสาม แล้ว join ด้วย DuckDB
# vector 3 มิติ แต่ละมิติคือหัวข้อ `[code, memory, deploy]` คิดตามได้ด้วยมือ

# %%
# %pip install -q lancedb pandas duckdb

# %%
import lancedb
import duckdb

db = lancedb.connect("./data")

# %% [markdown]
# **episodic** — เหตุการณ์ดิบ มี session กับเวลา
# แถวหนึ่งคือ "ตอนนั้นเกิดสิ่งนี้" ไม่ตีความ

# %%
episodic = db.create_table("episodic", data=[
    {"event_id": 1, "session": "s1", "ts": "2026-09-10T09:00", "text": "ran lesson 1, saw 2 fragments",       "vector": [0.9, 0.1, 0.0]},
    {"event_id": 2, "session": "s1", "ts": "2026-09-10T09:20", "text": "update wrote _deletions file",        "vector": [0.3, 0.7, 0.0]},
    {"event_id": 3, "session": "s2", "ts": "2026-09-10T13:00", "text": "int->float cast refused",             "vector": [0.6, 0.4, 0.0]},
    {"event_id": 4, "session": "s2", "ts": "2026-09-10T13:30", "text": "lancedb cannot run on Cloudflare",   "vector": [0.0, 0.2, 0.8]},
], mode="overwrite")

# %% [markdown]
# **semantic** — ข้อเท็จจริงที่กลั่นจากเหตุการณ์
# `source_event` ชี้กลับไปว่ารู้มาจากไหน ไม่มี foreign key ใน Lance เราเก็บเอง

# %%
semantic = db.create_table("semantic", data=[
    {"fact_id": 10, "source_event": 1, "text": "one write = one fragment",              "vector": [0.8, 0.2, 0.0]},
    {"fact_id": 11, "source_event": 2, "text": "Lance never rewrites, only appends",    "vector": [0.2, 0.8, 0.0]},
    {"fact_id": 12, "source_event": 3, "text": "type change = add, drop, rename",       "vector": [0.5, 0.5, 0.0]},
    {"fact_id": 13, "source_event": 4, "text": "native module needs real filesystem",   "vector": [0.0, 0.1, 0.9]},
], mode="overwrite")

# %% [markdown]
# **procedural** — วิธีทำ ขั้นตอนที่ใช้ซ้ำได้
# `uses_fact` บอกว่า skill นี้พึ่ง fact ไหน

# %%
procedural = db.create_table("procedural", data=[
    {"skill_id": 100, "uses_fact": 12, "steps": "add_columns(CAST) -> drop_columns -> alter_columns(rename)", "vector": [0.5, 0.5, 0.0]},
    {"skill_id": 101, "uses_fact": 11, "steps": "compact_files() then cleanup_old_versions()",               "vector": [0.1, 0.9, 0.0]},
    {"skill_id": 102, "uses_fact": 13, "steps": "deploy on a VM or container, not Workers",                  "vector": [0.0, 0.2, 0.8]},
], mode="overwrite")

# %% [markdown]
# **Recall** — คำถาม "เรื่อง memory" = vector `[0, 1, 0]`
# ยิง vector เดียวกันใส่ทั้งสามตาราง แต่ละตารางตอบในภาษาของตัวเอง
# episodic ตอบว่าเกิดอะไร semantic ตอบว่ารู้อะไร procedural ตอบว่าทำยังไง

# %%
q = [0.0, 1.0, 0.0]
for name, tbl in [("episodic", episodic), ("semantic", semantic), ("procedural", procedural)]:
    hit = tbl.search(q).limit(1).to_list()[0]
    text = hit.get("text") or hit.get("steps")
    print(f"{name:<11} d={hit['_distance']:.2f}  {text}")

# %% [markdown]
# **Join** — ตามสายจาก skill กลับไปหาเหตุการณ์ต้นทาง
# Lance ไม่ join ให้ ดึงเป็น Arrow แล้ว DuckDB ทำ เหมือนบทที่ 5

# %%
e, s, p = episodic.to_arrow(), semantic.to_arrow(), procedural.to_arrow()

duckdb.sql("""
    SELECT p.skill_id, s.text AS fact, e.session, e.ts, e.text AS event
    FROM p
    JOIN s ON s.fact_id = p.uses_fact
    JOIN e ON e.event_id = s.source_event
    ORDER BY p.skill_id
""").df()

# %% [markdown]
# **Session filter + vector** — ความจำเฉพาะ session `s2` เรื่อง code
# `where` กรอง session ก่อน แล้วค่อยวัดระยะ (บทที่ 14 จะดูว่าลำดับนี้สำคัญยังไง)

# %%
episodic.search([1.0, 0.0, 0.0]).where("session = 's2'").limit(2).to_pandas()[["event_id", "session", "text", "_distance"]]

# %% [markdown]
# บน disk คือสาม directory แยกกัน แต่ละอันมี manifest ของตัวเอง
# ไม่มีอะไรผูกกันในระดับไฟล์ ความสัมพันธ์ทั้งหมดอยู่ใน column ที่เราตั้งชื่อเอง

# %%
from pathlib import Path
for d in sorted(Path("data").glob("*.lance")):
    n = len(list((d / "data").iterdir()))
    print(f"{d.name:<18} fragments={n}")
