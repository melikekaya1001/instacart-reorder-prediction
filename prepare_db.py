import os, sqlite3
import pandas as pd

SEED, N_USERS = 42, 10_000
DB = "data/db.sqlite"
if os.path.exists(DB):
    os.remove(DB)
conn = sqlite3.connect(DB)

orders = pd.read_csv("data/orders.csv")
train_users = orders.loc[orders.eval_set == "train", "user_id"].drop_duplicates()
sampled = train_users.sample(N_USERS, random_state=SEED)
orders = orders[orders.user_id.isin(sampled)]
orders.to_sql("orders", conn, index=False)
order_ids = set(orders.order_id)

for name in ["order_products__prior", "order_products__train"]:
    for chunk in pd.read_csv(f"data/{name}.csv", chunksize=2_000_000):
        chunk[chunk.order_id.isin(order_ids)].to_sql(name, conn, index=False, if_exists="append")

for name in ["products", "aisles", "departments"]:
    pd.read_csv(f"data/{name}.csv").to_sql(name, conn, index=False)

conn.execute("CREATE INDEX idx_prior_order ON order_products__prior(order_id)")
conn.execute("CREATE INDEX idx_train_order ON order_products__train(order_id)")
conn.commit()
print("db hazir:", len(orders), "siparis")