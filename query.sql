-- Sorgu 1: kullanici-urun cifti ozellik + etiket tablosu (siniflandirma)
WITH po AS (
  SELECT order_id, user_id, order_number, days_since_prior_order
  FROM orders WHERE eval_set = 'prior'
),
user_stats AS (
  SELECT user_id, MAX(order_number) AS n_prior_orders,
         AVG(days_since_prior_order) AS avg_gap_days
  FROM po GROUP BY user_id
),
pairs AS (
  SELECT po.user_id, op.product_id,
         COUNT(*) AS times_bought,
         MAX(po.order_number) AS last_order_number
  FROM po JOIN order_products__prior op ON op.order_id = po.order_id
  GROUP BY po.user_id, op.product_id
),
product_stats AS (
  SELECT product_id,
         COUNT(*) AS product_n_users,
         AVG(CASE WHEN times_bought > 1 THEN 1.0 ELSE 0 END) AS product_reorder_rate
  FROM pairs GROUP BY product_id
),
train_items AS (
  SELECT o.user_id, otr.product_id
  FROM orders o JOIN order_products__train otr ON otr.order_id = o.order_id
  WHERE o.eval_set = 'train'
)
SELECT p.user_id, p.product_id, p.times_bought, u.n_prior_orders,
       u.n_prior_orders - p.last_order_number AS orders_since_last,
       1.0 * p.times_bought / u.n_prior_orders AS purchase_rate,
       u.avg_gap_days, ps.product_n_users, ps.product_reorder_rate,
       CASE WHEN t.product_id IS NOT NULL THEN 1 ELSE 0 END AS label
FROM pairs p
JOIN user_stats u USING (user_id)
JOIN product_stats ps USING (product_id)
LEFT JOIN train_items t ON t.user_id = p.user_id AND t.product_id = p.product_id;

-- Sorgu 2: kullanici bazli ozet tablo (kumeleme)
WITH basket AS (
  SELECT order_id, COUNT(*) AS basket_size, AVG(reordered) AS reorder_ratio
  FROM order_products__prior GROUP BY order_id
)
SELECT o.user_id, MAX(o.order_number) AS n_orders,
       AVG(b.basket_size) AS avg_basket_size,
       AVG(o.days_since_prior_order) AS avg_gap_days,
       AVG(b.reorder_ratio) AS reorder_ratio,
       AVG(o.order_hour_of_day) AS avg_hour,
       AVG(CASE WHEN o.order_dow IN (0, 1) THEN 1.0 ELSE 0 END) AS weekend_ratio
FROM orders o JOIN basket b ON b.order_id = o.order_id
WHERE o.eval_set = 'prior'
GROUP BY o.user_id;