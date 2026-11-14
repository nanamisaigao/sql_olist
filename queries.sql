
-- 业务指标：全平台已完成订单的 GMV、运费总额与真实客单价

SELECT (SUM(i.price) + SUM(i.freight_value)) / 100.0                              AS 已完成商品总额（GMV）,
       SUM(i.freight_value) / 100.0                                               AS 运费,
       COUNT(DISTINCT o.order_id)                                                 AS 真实订单数,
       (SUM(i.price) + SUM(i.freight_value)) / COUNT(DISTINCT o.order_id) / 100.0 AS 客单价
FROM orders AS o
         JOIN order_items AS i ON o.order_id = i.order_id
WHERE o.order_status = 'delivered';

-- [gmv]
WITH item_summary AS (
    SELECT
        order_id,
        SUM(price + freight_value) AS total_item_value
    FROM order_items
    GROUP BY order_id
),
payment_summary AS (
    SELECT
        order_id,
        SUM(payment_value) AS total_payment_value
    FROM payments
    GROUP BY order_id
)
SELECT
        COUNT(DISTINCT o.order_id)                                             AS 真实订单数,
        SUM(i.total_item_value) / 100.0                                        AS 已完成商品总额_GMV,
        SUM(p.total_payment_value) / 100.0                                     AS 已支付商品总额,
        ROUND(SUM(i.total_item_value) * 100.0 / SUM(p.total_payment_value), 2) AS 对账率百分比
FROM orders o
JOIN item_summary i ON o.order_id = i.order_id
JOIN payment_summary p ON o.order_id = p.order_id
WHERE o.order_status = 'delivered';

-- 业务指标：用户月度留存矩阵
-- [cd]
WITH orders_id AS (
   SELECT DISTINCT
    c.customer_unique_id,
    strftime('%Y-%m', order_purchase_timestamp) AS 月份,
    CAST(strftime('%Y', o.order_purchase_timestamp) AS INTEGER) * 12 +
        CAST(strftime('%m', o.order_purchase_timestamp) AS INTEGER) AS 月份序列
    FROM orders AS o
    JOIN customers AS c ON c.customer_id=o.customer_id
    WHERE order_status='delivered'

),
first_buy AS(
    SELECT
        customer_unique_id,
        min(月份序列) AS 首购序列
    FROM orders_id
    GROUP BY customer_unique_id
    ),
cohort_data AS(
    SELECT
        o.customer_unique_id AS user_id,
        printf('%04d-%02d',(f.首购序列 - 1) / 12,(f.首购序列 - 1) % 12 + 1) AS 首购月份,
        o.月份序列 - f.首购序列 AS 月份差额
    FROM orders_id AS o
    JOIN first_buy  AS f ON f.customer_unique_id=o.customer_unique_id
)
SELECT

    c.首购月份,
    COUNT(DISTINCT case when 月份差额=0 then c.user_id end ) AS 第0月留存,
    COUNT(DISTINCT case when 月份差额=1 then c.user_id end ) AS 第1月留存,
    COUNT(DISTINCT case when 月份差额=2 then c.user_id end ) AS 第2月留存,
    COUNT(DISTINCT case when 月份差额=3 then c.user_id end ) AS 第3月留存
FROM cohort_data AS c
GROUP BY c.首购月份
ORDER BY c.首购月份;

--用户留存率计算
-- [urr]
WITH orders_id AS (
   SELECT
    c.customer_unique_id,
    strftime('%Y-%m', order_purchase_timestamp) AS 月份,
    CAST(strftime('%Y', o.order_purchase_timestamp) AS INTEGER) * 12 +
        CAST(strftime('%m', o.order_purchase_timestamp) AS INTEGER) AS 月份序列
    FROM orders AS o
    JOIN customers AS c ON c.customer_id=o.customer_id
    WHERE order_status='delivered'

),
first_buy AS(
    SELECT
        customer_unique_id,
        min(月份序列) AS 首购序列
    FROM orders_id
    GROUP BY customer_unique_id
    ),
cohort_data AS(
    SELECT
        o.customer_unique_id AS user_id,
        printf('%04d-%02d',(f.首购序列 - 1) / 12,(f.首购序列 - 1) % 12 + 1) AS 首购月份,
        o.月份序列 - f.首购序列 AS 月份差额
    FROM orders_id AS o
    JOIN first_buy  AS f ON f.customer_unique_id=o.customer_unique_id
)
SELECT
    c.首购月份,
    round(COUNT(DISTINCT case when 月份差额=1 then c.user_id end )*1.0/COUNT(DISTINCT c.user_id)*100.0,2) AS 次月留存率
FROM cohort_data AS c
WHERE 首购月份!= '2016-12'
GROUP BY c.首购月份
ORDER BY c.首购月份;



-- RFM 模型（用户价值分层）
-- [rfm]
WITH orders_id AS (
   SELECT DISTINCT
    c.customer_unique_id,
    julianday(date (o.order_purchase_timestamp)) AS 时间序列,
    order_id
    FROM orders AS o
    JOIN customers AS c ON c.customer_id=o.customer_id
    WHERE order_status='delivered'

),
user_buy AS(
    SELECT
        customer_unique_id,
        max(时间序列) AS 最晚购物时间
    FROM orders_id
    GROUP BY customer_unique_id
),
rfm AS (
    SELECT
        o.customer_unique_id,
        (SELECT MAX(时间序列) FROM orders_id)- f.最晚购物时间 AS 最近消费天数,
        COUNT(DISTINCT o.order_id) AS 消费频率,
        SUM(i.price+i.freight_value)/100.0 AS 消费金额
    FROM orders_id AS o
    JOIN user_buy AS f ON o.customer_unique_id=f.customer_unique_id
    JOIN order_items AS i ON i.order_id=o.order_id
    GROUP BY o.customer_unique_id
),
rfm_score AS (
    SELECT
    customer_unique_id,
    最近消费天数,
    消费频率,
    消费金额,
    ntile(5) over (ORDER BY 最近消费天数 desc ) R分,
     CASE
            WHEN 消费频率 = 1 THEN 1
            WHEN 消费频率 = 2 THEN 3
            WHEN 消费频率 >= 3 THEN 5
            ELSE 1
        END AS F分,
    ntile(5) over (ORDER BY 消费金额 asc ) m分
    FROM rfm
),
rfm_label AS (
    SELECT
    *,
     CASE

            WHEN R分 >= 3 AND F分 >= 3 AND M分 >= 3 THEN '重要价值客户'
            WHEN R分 < 3  AND F分 >= 3 AND M分 >= 3 THEN '重要保持客户'
            WHEN R分 >= 3 AND F分 < 3  AND M分 >= 3 THEN '重要发展客户'
            WHEN R分 < 3  AND F分 < 3  AND M分 >= 3 THEN '重要挽留客户'
            WHEN R分 >= 3 AND F分 >= 3 AND M分 < 3  THEN '一般价值客户'
            WHEN R分 < 3  AND F分 >= 3 AND M分 < 3  THEN '一般保持客户'
            WHEN R分 >= 3 AND F分 < 3  AND M分 < 3  THEN '一般发展客户'
            WHEN R分 < 3  AND F分 < 3  AND M分 < 3  THEN '一般挽留客户'
        END AS 客户类型
    FROM rfm_score
)

SELECT * FROM rfm_label ;

-- RFM客户占比
-- [rfm_summary]

WITH orders_id AS (
   SELECT DISTINCT
    c.customer_unique_id,
    julianday(date (o.order_purchase_timestamp)) AS 时间序列,
    order_id
    FROM orders AS o
    JOIN customers AS c ON c.customer_id=o.customer_id
    WHERE order_status='delivered'

),
user_buy AS(
    SELECT
        customer_unique_id,
        max(时间序列) AS 最晚购物时间
    FROM orders_id
    GROUP BY customer_unique_id
),
rfm AS (
    SELECT
        o.customer_unique_id,
        (SELECT MAX(时间序列) FROM orders_id)- f.最晚购物时间 AS 最近消费天数,
        COUNT(DISTINCT o.order_id) AS 消费频率,
        SUM(i.price+i.freight_value)/100.0 AS 消费金额
    FROM orders_id AS o
    JOIN user_buy AS f ON o.customer_unique_id=f.customer_unique_id
    JOIN order_items AS i ON i.order_id=o.order_id
    GROUP BY o.customer_unique_id
),
rfm_score AS (
    SELECT
    customer_unique_id,
    最近消费天数,
    消费频率,
    消费金额,
    ntile(5) over (ORDER BY 最近消费天数 desc ) R分,
     CASE
            WHEN 消费频率 = 1 THEN 1
            WHEN 消费频率 = 2 THEN 3
            WHEN 消费频率 >= 3 THEN 5
            ELSE 1
        END AS F分,
    ntile(5) over (ORDER BY 消费金额 asc ) m分
    FROM rfm
),
rfm_label AS (
    SELECT
    *,
     CASE

            WHEN R分 >= 3 AND F分 >= 3 AND M分 >= 3 THEN '重要价值客户'
            WHEN R分 < 3  AND F分 >= 3 AND M分 >= 3 THEN '重要保持客户'
            WHEN R分 >= 3 AND F分 < 3  AND M分 >= 3 THEN '重要发展客户'
            WHEN R分 < 3  AND F分 < 3  AND M分 >= 3 THEN '重要挽留客户'
            WHEN R分 >= 3 AND F分 >= 3 AND M分 < 3  THEN '一般价值客户'
            WHEN R分 < 3  AND F分 >= 3 AND M分 < 3  THEN '一般保持客户'
            WHEN R分 >= 3 AND F分 < 3  AND M分 < 3  THEN '一般发展客户'
            WHEN R分 < 3  AND F分 < 3  AND M分 < 3  THEN '一般挽留客户'
        END AS 客户类型
    FROM rfm_score
)
SELECT
    客户类型,
    COUNT(*) AS 用户数,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM rfm_label), 2) AS 人数占比,
    ROUND(AVG(最近消费天数), 1) AS 人均最近消费天数,
    ROUND(AVG(消费频率), 1) AS 人均消费频率,
    ROUND(AVG(消费金额), 2) AS 人均消费金额
    FROM rfm_label
    GROUP BY 客户类型
    ;

