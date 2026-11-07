-- -- 客户表
--
-- create table customers(
--   customer_id TEXT PRIMARY KEY,
--   customer_unique_id TEXT,
--   customer_zip_code_prefix INTEGER,
--   customer_city TEXT,
--   customer_state TEXT
--
-- );
-- -- 卖家表（3,095 个卖家）
--
-- CREATE TABLE sellers(
--     seller_id TEXT PRIMARY KEY,
--     seller_zip_code_prefix INTEGER,
--     seller_city TEXT,
--     seller_state TEXT
--
-- );
-- --  商品表
--
-- CREATE TABLE products(
--     product_id	TEXT PRIMARY KEY,
--     product_category_name TEXT,
--     product_name_lenght INTEGER,
--     product_description_lenght INTEGER,
--     product_photos_qty INTEGER,
--     product_weight_g INTEGER,
--     product_length_cm INTEGER,
--     product_height_cm INTEGER,
--     product_width_cm INTEGER
-- );
-- -- 订单主表
-- CREATE TABLE orders(
--     order_id TEXT primary key ,
--     customer_id text,
--     order_status text,
--     order_purchase_timestamp text,
--     order_approved_at TEXT,
--     order_delivered_carrier_date TEXT,
--     order_delivered_customer_date TEXT,
--     order_estimated_delivery_date TEXT,
--     FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
-- );
-- -- 订单商品明细
-- CREATE TABLE order_items(
--     order_id TEXT,
--     order_item_id INTEGER,
--     product_id TEXT,
--     seller_id TEXT,
--     shipping_limit_date TEXT,
--     price INTEGER,
--     freight_value INTEGER,
--     PRIMARY KEY (order_id,order_item_id),
--     FOREIGN KEY (order_id) REFERENCES orders(order_id),
--     FOREIGN KEY (product_id) REFERENCES products(product_id),
--     FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
-- );
-- -- 支付记录
-- CREATE TABLE payments (
--     order_id TEXT,
--     payment_sequential INTEGER,
--     payment_type TEXT,
--     payment_installments INTEGER,
--     payment_value INTEGER,
--     PRIMARY KEY (order_id, payment_sequential),
--     FOREIGN KEY (order_id) REFERENCES orders(order_id)
-- );

-- 业务指标：全平台已完成订单的 GMV、运费总额与真实客单价
select
    (sum(i.price)+sum(i.freight_value))/100.0 as 已完成商品总额,
    sum(i.freight_value)/100.0 as 运费,
    COUNT(DISTINCT o.order_id) as 真实订单数,
    (sum(i.price)+sum(i.freight_value))/COUNT(DISTINCT o.order_id)/100.0 as 客单价
    from orders as o
    join order_items as i on o.order_id=i.order_id
    where o.order_status='delivered';


-- 业务指标：用户月度留存矩阵
with orders_id as (
   select
    c.customer_unique_id,
    strftime('%Y-%m', order_purchase_timestamp) as 月份,
    CAST(strftime('%Y', o.order_purchase_timestamp) AS INTEGER) * 12 +
        CAST(strftime('%m', o.order_purchase_timestamp) AS INTEGER) AS 月份序列
    from orders as o
    join customers as c on c.customer_id=o.customer_id
    where order_status='delivered'
    group by c.customer_unique_id, 月份, 月份序列
),
first_buy as(
    select
        customer_unique_id,
        min(月份) as 首购月份,
        min(月份序列) as 首购序列
    from orders_id
    GROUP BY customer_unique_id
    ),
cohort_data as(
    select
        o.customer_unique_id as user_id,
        f.首购月份,
        o.月份序列 - f.首购序列 AS 月份差额
    from orders_id as o
    join first_buy  as f on f.customer_unique_id=o.customer_unique_id
)
SELECT
    f.首购月份,
    COUNT(DISTINCT case when 月份差额=0 then c.user_id end ) AS 第0月留存,
    COUNT(DISTINCT case when 月份差额=1 then c.user_id end ) AS 第1月留存,
    COUNT(DISTINCT case when 月份差额=2 then c.user_id end ) AS 第2月留存,
    COUNT(DISTINCT case when 月份差额=3 then c.user_id end ) AS 第3月留存
FROM cohort_data as c
join first_buy f on f.customer_unique_id=c.user_id
GROUP BY f.首购月份
ORDER BY f.首购月份;


