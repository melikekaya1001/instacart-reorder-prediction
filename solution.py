import sqlite3
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import f1_score, average_precision_score, precision_recall_curve, silhouette_score

SEED = 42
np.random.seed(SEED)

conn = sqlite3.connect("data/db.sqlite")
q_pairs, q_users = [s for s in open("query.sql", encoding="utf-8").read().split(";") if s.strip()]
df = pd.read_sql(q_pairs, conn)
users = pd.read_sql(q_users, conn)
df["avg_gap_days"] = df["avg_gap_days"].fillna(df["avg_gap_days"].median())
results = []

# ---------- GOREV A: siniflandirma ----------
feats = ["times_bought", "n_prior_orders", "orders_since_last", "purchase_rate",
         "avg_gap_days", "product_n_users", "product_reorder_rate"]
uid = df.user_id.unique()
tr_u, te_u = train_test_split(uid, test_size=0.2, random_state=SEED)
tr_u, va_u = train_test_split(tr_u, test_size=0.2, random_state=SEED)   # kullanici bazli ayrim
tr, va, te = [df[df.user_id.isin(u)] for u in (tr_u, va_u, te_u)]

def best_threshold(y, p):
    pr, rc, th = precision_recall_curve(y, p)
    f1 = 2 * pr * rc / (pr + rc + 1e-9)
    return th[np.argmax(f1[:-1])]

# baseline: gecmiste >=2 kez alinan urun tekrar alinir
results += [["baseline_kural", "f1", f1_score(te.label, (te.times_bought >= 2).astype(int))],
            ["baseline_kural", "pr_auc", average_precision_score(te.label, te.times_bought)]]

scaler = StandardScaler().fit(tr[feats])
models = {
    "logreg": (LogisticRegression(max_iter=1000, class_weight="balanced"), True),
    "hist_gb": (HistGradientBoostingClassifier(random_state=SEED), False),
}
for name, (m, scale) in models.items():
    f = (lambda d: scaler.transform(d[feats])) if scale else (lambda d: d[feats])
    m.fit(f(tr), tr.label)
    th = best_threshold(va.label, m.predict_proba(f(va))[:, 1])      # esik validation'dan
    p = m.predict_proba(f(te))[:, 1]
    results += [[name, "f1", f1_score(te.label, (p >= th).astype(int))],
                [name, "pr_auc", average_precision_score(te.label, p)],
                [name, "threshold", th]]

# ---------- GOREV B: kumeleme ----------
cf = ["n_orders", "avg_basket_size", "avg_gap_days", "reorder_ratio", "avg_hour", "weekend_ratio"]
users["avg_gap_days"] = users["avg_gap_days"].fillna(users["avg_gap_days"].median())
Xs = StandardScaler().fit_transform(users[cf])
best_k, best_s = None, -1
for k in range(3, 7):
    lab = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit_predict(Xs)
    s = silhouette_score(Xs, lab, sample_size=5000, random_state=SEED)
    results.append([f"kmeans_k{k}", "silhouette", s])
    if s > best_s:
        best_k, best_s = k, s
users["cluster"] = KMeans(n_clusters=best_k, n_init=10, random_state=SEED).fit_predict(Xs)

pd.DataFrame(results, columns=["deney", "metrik", "deger"]).to_csv("results.csv", index=False)

# ---------- GORSELLER ----------
plt.figure(figsize=(7, 4))
df.assign(tb=df.times_bought.clip(upper=10)).groupby("tb").label.mean().plot.bar(color="#3b7")
plt.title("Urunun gecmişte alinma sayisina gore tekrar alinma olasiligi")
plt.xlabel("times_bought (10 ve ustu birlestirildi)"); plt.ylabel("Sonraki siparişte alinma orani")
plt.savefig("figures/fig1_reorder_by_times_bought.png", dpi=150, bbox_inches="tight"); plt.close()

prof = users.groupby("cluster")[cf].mean()
(prof - prof.mean()) / prof.std()
((prof - prof.mean()) / prof.std()).plot.bar(figsize=(9, 4.5))
plt.title(f"Kullanici segmentleri (k={best_k}): standartlastirilmis ortalamalar")
plt.xlabel("Küme"); plt.ylabel("Ortalamadan sapma (z)"); plt.legend(fontsize=7)
plt.savefig("figures/fig2_cluster_profiles.png", dpi=150, bbox_inches="tight"); plt.close()

r = pd.DataFrame(results, columns=["deney", "metrik", "deger"])
r[r.metrik == "f1"].set_index("deney").deger.plot.bar(figsize=(5, 4), color="#58c")
plt.title("Test setinde F1: baseline ve modeller"); plt.ylabel("F1")
plt.savefig("figures/fig3_f1_comparison.png", dpi=150, bbox_inches="tight"); plt.close()
print(r)