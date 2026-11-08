import pandas as pd
import sqlite3

def save_excel(df_data,filename):
    with pd.ExcelWriter(filename,engine='openpyxl') as writer:
        for sheet_name,df in df_data.items():
            df.to_excel(writer,sheet_name=sheet_name,index=False)
    print(f"报表已成功保存至 {filename}")

def get_gmv_report(conn):
    gmv_report="""
    select
    (sum(i.price)+sum(i.freight_value))/100.0 as 已完成商品总额,
    sum(i.freight_value)/100.0 as 运费,
    COUNT(DISTINCT o.order_id) as 真实订单数,
    (sum(i.price)+sum(i.freight_value))/COUNT(DISTINCT o.order_id)/100.0 as 客单价
    from orders as o
    join order_items as i on o.order_id=i.order_id
    where o.order_status='delivered';
    
    
    """
    df_gmv_report=pd.read_sql(gmv_report,conn)
    return df_gmv_report

def get_retention_matrix_label(conn):
    retention_matrix_label="""
        with orders_id as (
   select DISTINCT
    c.customer_unique_id,
    strftime('%Y-%m', order_purchase_timestamp) as 月份,
    CAST(strftime('%Y', o.order_purchase_timestamp) AS INTEGER) * 12 +
        CAST(strftime('%m', o.order_purchase_timestamp) AS INTEGER) AS 月份序列
    from orders as o
    join customers as c on c.customer_id=o.customer_id
    where order_status='delivered'

),
first_buy as(
    select
        customer_unique_id,
        min(月份序列) as 首购序列
    from orders_id
    GROUP BY customer_unique_id
    ),
cohort_data as(
    select
        o.customer_unique_id as user_id,
printf('%04d-%02d',
       (f.首购序列 - 1) / 12,
       (f.首购序列 - 1) % 12 + 1) AS 首购月份,
        o.月份序列 - f.首购序列 AS 月份差额
    from orders_id as o
    join first_buy  as f on f.customer_unique_id=o.customer_unique_id
)
SELECT

    c.首购月份,
    COUNT(DISTINCT case when 月份差额=0 then c.user_id end ) AS 第0月留存,
    COUNT(DISTINCT case when 月份差额=1 then c.user_id end ) AS 第1月留存,
    COUNT(DISTINCT case when 月份差额=2 then c.user_id end ) AS 第2月留存,
    COUNT(DISTINCT case when 月份差额=3 then c.user_id end ) AS 第3月留存
FROM cohort_data as c
GROUP BY c.首购月份
ORDER BY c.首购月份;
    
    """
    df_retention_matrix_label=pd.read_sql(retention_matrix_label,conn)
    return df_retention_matrix_label

def get_rfm_report(conn):
    rfm_report="""
    with orders_id as (
   select DISTINCT
    c.customer_unique_id,
    julianday(date (o.order_purchase_timestamp)) AS 时间序列,
    order_id
    from orders as o
    join customers as c on c.customer_id=o.customer_id
    where order_status='delivered'

),
user_buy as(
    select
        customer_unique_id,
        max(时间序列) as 最晚购物时间
    from orders_id
    GROUP BY customer_unique_id
),
rfm as (
    select
        o.customer_unique_id,
        (SELECT MAX(时间序列) FROM orders_id)- f.最晚购物时间 as 最近消费天数,
        count(DISTINCT o.order_id) as 消费频率,
        sum(i.price+i.freight_value)/100.0 as 消费金额
    from orders_id as o
    join user_buy as f on o.customer_unique_id=f.customer_unique_id
    join order_items as i on i.order_id=o.order_id
    group by o.customer_unique_id
),
rfm_score as (
    select
    customer_unique_id,
    最近消费天数,
    消费频率,
    消费金额,
    ntile(5) over (order by 最近消费天数 desc ) R分,
     CASE
            WHEN 消费频率 = 1 THEN 1
            WHEN 消费频率 = 2 THEN 3
            WHEN 消费频率 >= 3 THEN 5
            ELSE 1
        END AS F分,
    ntile(5) over (order by 消费金额 asc ) m分
    from rfm
),
rfm_label as (
    select
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
    from rfm_score
)

SELECT * FROM rfm_label ;
    
    
    """
    df_rfm_report=pd.read_sql(rfm_report,conn)
    return df_rfm_report

def main():
    conn = sqlite3.connect('olist.db')
    print("正在计算大盘指标...")
    df_gmv=get_gmv_report(conn)
    print("正在计算留存矩阵...")
    df_retention_matrix=get_retention_matrix_label(conn)
    print("正在计算 RFM 模型...")
    df_rfm=get_rfm_report(conn)
    report_data={
        "大盘核心指标": df_gmv,
        "用户留存矩阵":df_retention_matrix,
        "用户价值分层": df_rfm
    }
    save_excel(report_data, "电商分析报表.xlsx")
    conn.close()

if __name__ == "__main__":
    main()