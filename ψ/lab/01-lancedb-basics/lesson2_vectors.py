# %% [markdown]
# # Lesson 2 — vectors
# A vector is a list of floats, same length every row. Search returns rows plus a `_distance` column.

# %%
import lancedb

db = lancedb.connect("./data/lesson2")

# %%
rows = [
    {"id": "a", "vector": [1.0, 0.0, 0.0]},
    {"id": "b", "vector": [0.0, 1.0, 0.0]},
    {"id": "c", "vector": [0.0, 0.0, 1.0]},
    {"id": "d", "vector": [0.9, 0.1, 0.0]},  # close to a
    {"id": "e", "vector": [0.5, 0.5, 0.0]},  # between a and b
]
tbl = db.create_table("points", data=rows, mode="overwrite")
tbl.schema  # vector: fixed_size_list<float>[3]

# %%
tbl.to_pandas()

# %%
# Which row is nearest to [1, 0, 0]?
q = [1.0, 0.0, 0.0]
tbl.search(q).limit(3).to_pandas()
# _distance = squared L2 by default. a=0, d=0.02, e=0.5

# %%
# Same query, cosine metric. Direction only, length ignored.
tbl.search(q).metric("cosine").limit(3).to_pandas()
