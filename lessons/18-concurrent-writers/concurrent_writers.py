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

DB = pathlib.Path("./data").resolve()
shutil.rmtree(DB, ignore_errors=True)
db = lancedb.connect(str(DB))
tbl = db.create_table("memories", data=[{"id": 0, "agent": "seed", "n": 0}], mode="overwrite")

# %% [markdown]
# script ของ worker หนึ่งคน รับชื่อ agent กับ offset
# id ชนกันครึ่งหนึ่ง (`offset + i`) อีกครึ่งแยกกัน (`agent` ต่างกัน id เดิม ก็คือ update ทับ)
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
# เก็บ stderr ไว้ดูว่า Lance บ่นเรื่อง conflict ไหม

# %%
procs = [
    subprocess.Popen([sys.executable, "worker.py", str(DB), a, str(off)], stderr=subprocess.PIPE, text=True)
    for a, off in [("A", 1), ("B", 11)]
]
logs = [p.communicate()[1] for p in procs]
for a, log in zip("AB", logs):
    lines = [l for l in log.splitlines() if "WARN" not in l]
    print(a, "->", " | ".join(lines[-3:]))

# %% [markdown]
# **นับผล** — ควรได้ 31 แถว (seed 1 + id 1–30) ถ้า write หายจะได้น้อยกว่านี้
# version ควรเป็น 41 (create 1 + merge_insert 40) ทุก write คือ manifest ใหม่ ไม่มีรวบ
# id 11–20 ที่ชนกัน รันนี้ A ชนะทั้งหมด (A 20 แถว B 10 แถว) เพราะ A ไปถึง id 11 ทีหลัง B
# รันใหม่อาจสลับ ขึ้นกับว่าใครถึงก่อน แต่รวมต้อง 31 เสมอ

# %%
tbl = db.open_table("memories")
print("rows:", tbl.count_rows(), "| version:", tbl.version)
df = tbl.to_pandas().sort_values("id")
print(df.groupby("agent").size().to_dict())
df[(df.id >= 9) & (df.id <= 13)]

# %% [markdown]
# **ทำไมไม่หาย** — Lance ใช้ optimistic concurrency
# ก่อน commit อ่าน version ล่าสุด เขียน manifest ชื่อ version+1
# ถ้าชื่อนั้นมีคนเขียนไปแล้ว (อีก process เร็วกว่า) commit ล้มเหลว อ่าน version ใหม่ ลองอีก
# retry สูงสุด 20 ครั้ง (ค่า default) เกินนั้นได้ error `Commit conflict ... after 20 retries` (lancedb GH #2426)
#
# รันนี้ 40 write สอง process มี conflict แน่นอน แต่ retry จบในไม่กี่ ms เลยไม่เห็น error
# จะเห็น error จริงต้องมี writer เยอะกว่านี้มาก หรือ storage ช้า (S3) ทำให้ retry หมดโควตา
# บทนี้ไม่ได้ทำให้พังให้ดู แค่แสดงว่าทางปกติมันรอด

# %%
from pathlib import Path
root = Path("data/memories.lance")
print("manifests:", len(list((root / "_versions").glob("*.manifest"))))
print("txn files:", len(list((root / "_transactions").glob("*.txn"))))
print("fragments:", len(list((root / "data").glob("*.lance"))))
pathlib.Path("worker.py").unlink()
