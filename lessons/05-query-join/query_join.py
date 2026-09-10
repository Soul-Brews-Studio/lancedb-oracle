# %% [markdown]
# # Lesson 5 — query & join · ค้นและเชื่อมตาราง
#
# `where` ของ LanceDB รับ SQL แค่ส่วน filter ไม่มี JOIN ไม่มี GROUP BY
# บทนี้ทำ query ที่มีให้ก่อน แล้วค่อยดูว่าพอต้อง join จะทำยังไง
# คำตอบสั้น ๆ คือ ดึงเป็น Arrow แล้วให้ pandas หรือ DuckDB ทำต่อ

# %%
# %pip install -q lancedb pandas duckdb

# %%
import lancedb

db = lancedb.connect("./data")

users = db.create_table("users", data=[
    {"id": 1, "name": "nat",  "plan": "team"},
    {"id": 2, "name": "beta", "plan": "pro"},
    {"id": 4, "name": "odin", "plan": "free"},
], mode="overwrite")

orders = db.create_table("orders", data=[
    {"order_id": 10, "user_id": 1, "amount": 300},
    {"order_id": 11, "user_id": 1, "amount": 120},
    {"order_id": 12, "user_id": 2, "amount": 80},
    {"order_id": 13, "user_id": 9, "amount": 50},  # user 9 does not exist
], mode="overwrite")

# %% [markdown]
# **Filter** `where` รับ `=` `>` `AND` `OR` `IN` `LIKE` `IS NULL`
# `select` เลือกเฉพาะ column ที่ต้องการ อ่านน้อยลง เร็วขึ้น
# `limit` จำเป็นเมื่อไม่มี vector search ไม่ใส่จะได้ค่า default 10

# %%
users.search().where("plan IN ('pro', 'team') AND name LIKE 'n%'").select(["id", "name"]).limit(10).to_pandas()

# %%
orders.search().where("amount > 100").to_pandas()

# %% [markdown]
# **Join แบบที่ 1 — pandas**
# ดึงสองตารางออกมาเป็น DataFrame แล้ว `merge`
# เหมาะกับตารางเล็ก ข้อมูลทั้งหมดขึ้น memory

# %%
u = users.to_pandas()
o = orders.to_pandas()
o.merge(u, left_on="user_id", right_on="id", how="left")[["order_id", "name", "plan", "amount"]]

# %% [markdown]
# **Join แบบที่ 2 — DuckDB**
# DuckDB อ่าน Arrow table ได้ตรง ๆ เขียน SQL เต็มรูปแบบได้เลย
# JOIN · GROUP BY · window function ครบ ไม่ต้องแปลงอะไร
#
# ตัวแปร Python ที่เป็น Arrow table ใช้ชื่อใน SQL ได้ทันที

# %%
import duckdb

users_arrow = users.to_arrow()
orders_arrow = orders.to_arrow()

duckdb.sql("""
    SELECT u.name, u.plan, COUNT(o.order_id) AS orders, SUM(o.amount) AS total
    FROM users_arrow u
    LEFT JOIN orders_arrow o ON o.user_id = u.id
    GROUP BY u.name, u.plan
    ORDER BY total DESC NULLS LAST
""").df()

# %% [markdown]
# order 13 ชี้ไป user 9 ที่ไม่มีอยู่
# LanceDB ไม่มี foreign key ไม่มีใครห้าม
# ความสัมพันธ์ระหว่างตาราง เป็นหน้าที่ของโค้ดฝั่งเรา ไม่ใช่ของ DB

# %%
duckdb.sql("""
    SELECT o.*
    FROM orders_arrow o
    LEFT JOIN users_arrow u ON o.user_id = u.id
    WHERE u.id IS NULL
""").df()
