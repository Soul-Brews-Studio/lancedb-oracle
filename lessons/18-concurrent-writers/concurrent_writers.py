# %% [markdown]
# # Lesson 18 — concurrent writers · สอง process เขียนตารางเดียวกันพร้อมกัน
#
# fleet มี agent หลายตัว แต่ละตัว `remember()` ลง Lance เดียวกัน ไม่มี server กลาง
# แล้วใครกันไม่ให้เขียนทับกัน คำตอบคือ manifest
# ทุก write ออก manifest ใหม่ ถ้าสองคนออก version เดียวกันพร้อมกัน คนที่ช้ากว่าต้อง retry
# บทนี้ปล่อยสอง process ยิง `merge_insert` ใส่ตารางเดียวกัน 20 ครั้งต่อคน แล้วนับ

# %%
# %pip install -q lancedb pandas

# %%
import lancedb, subprocess, sys, textwrap, pathlib, shutil
import pandas as pd

DB = pathlib.Path("./data").resolve()
shutil.rmtree(DB, ignore_errors=True)
db = lancedb.connect(str(DB))
tbl = db.create_table("memories", data=[{"id": 0, "agent": "seed", "n": 0}], mode="overwrite")
tbl.to_pandas()

# %% [markdown]
# script ของ worker หนึ่งคน รับชื่อ agent กับ offset
# เขียน id `offset + i` 20 ครั้ง `n` คือรอบที่เขียน
# `merge_insert("id")` เจอ id เดิม update ไม่เจอ insert คำสั่งเดียวปลอดภัยทั้งสองกรณี

# %%
WORKER = textwrap.dedent('''
    import sys, lancedb
    path, agent, offset = sys.argv[1], sys.argv[2], int(sys.argv[3])
    tbl = lancedb.connect(path).open_table("memories")
    for i in range(20):
        tbl.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(
            [{"id": offset + i, "agent": agent, "n": i}]
        )
    print(agent, "done", file=sys.stderr)
''')
_ = pathlib.Path("worker.py").write_text(WORKER)

# %% [markdown]
# ปล่อยสองคนพร้อมกัน A เขียน id 1–20 · B เขียน id 11–30
# id 11–20 ชนกัน ใครมาทีหลังชนะ (update) id อื่นไม่ชน (insert)
# เก็บ stderr ไว้ดูว่า Lance บ่นเรื่อง conflict ไหม ตารางข้างล่างคือบรรทัดสุดท้ายของแต่ละคน

# %%
procs = [
    subprocess.Popen([sys.executable, "worker.py", str(DB), a, str(off)], stderr=subprocess.PIPE, text=True)
    for a, off in [("A", 1), ("B", 11)]
]
logs = {a: p.communicate()[1] for a, p in zip("AB", procs)}
conflicts = sum(log.lower().count("conflict") for log in logs.values())
pd.DataFrame([{"agent": a, "ids written": rng, "last stderr line": [l for l in log.splitlines() if "WARN" not in l][-1],
               "mentions 'conflict'": log.lower().count("conflict")}
              for (a, log), rng in zip(logs.items(), ["1–20", "11–30"])])

# %% [markdown]
# **นับผล** — ควรได้ 31 แถว (seed 1 + id 1–30) ถ้า write หายจะได้น้อยกว่านี้
# version ควรเป็น 41 (create 1 + merge_insert 40) ทุก write คือ manifest ใหม่ ไม่มีรวบ
# manifests · txn · fragments ต้องเท่ากับ version ทั้งหมด หนึ่ง commit หนึ่งไฟล์ทุกชนิด

# %%
tbl = db.open_table("memories")
root = pathlib.Path("data/memories.lance")
pd.DataFrame([{
    "rows": tbl.count_rows(), "expected rows": 31,
    "version": tbl.version, "expected version": 41,
    "manifests": len(list((root / "_versions").glob("*.manifest"))),
    "txn files": len(list((root / "_transactions").glob("*.txn"))),
    "fragments": len(list((root / "data").glob("*.lance"))),
    "conflicts seen in stderr": conflicts,
}])

# %% [markdown]
# **ใครชนะ id ที่ชน** — ดู `last_writer` ของ id 9–13
# id 9 10 มีแต่ A เขียน · id 11–13 ทั้งคู่เขียน ค่าที่เหลือคือของคนที่ commit ทีหลัง
# รันนี้ A ชนะทุก id ที่ชน (ตารางถัดไปนับให้) รันใหม่อาจสลับ แต่รวมต้อง 31 เสมอ

# %%
df = tbl.to_pandas().sort_values("id").rename(columns={"agent": "last_writer", "n": "value"})
df["contested?"] = df.id.between(11, 20).map({True: "✓ (A and B both wrote)", False: ""})
df[df.id.between(9, 13)].reset_index(drop=True)

# %%
df[df.id > 0].groupby("last_writer").agg(rows_owned=("id", "count"), ids=("id", lambda s: f"{s.min()}–{s.max()}")).reset_index()

# %% [markdown]
# **ทำไมไม่หาย** — Lance ใช้ optimistic concurrency
# ก่อน commit อ่าน version ล่าสุด เขียน manifest ชื่อ version+1
# ถ้าชื่อนั้นมีคนเขียนไปแล้ว (อีก process เร็วกว่า) commit ล้มเหลว อ่าน version ใหม่ ลองอีก
# retry สูงสุด 20 ครั้ง (ค่า default) เกินนั้นได้ error `Commit conflict ... after 20 retries` (lancedb GH #2426)
#
# รันนี้ 40 write สอง process มี conflict แน่นอน แต่ retry จบในไม่กี่ ms เลยไม่เห็นใน stderr (0 ในตารางข้างบน)
# จะเห็น error จริงต้องมี writer เยอะกว่านี้มาก หรือ storage ช้า (S3) ทำให้ retry หมดโควตา
# บทนี้ไม่ได้ทำให้พังให้ดู แค่แสดงว่าทางปกติมันรอด
#
# manifest ทั้ง 41 ไฟล์ยังอยู่ ดูเวลาได้ว่า A กับ B สลับกัน commit

# %%
pathlib.Path("worker.py").unlink()
vs = tbl.list_versions()
pd.DataFrame([{"version": v["version"], "time": v["timestamp"].strftime("%H:%M:%S.%f")[:-3],
               "rows after": v["metadata"].get("total_rows", "")} for v in vs]).iloc[[0, 1, 2, 3, -3, -2, -1]]
