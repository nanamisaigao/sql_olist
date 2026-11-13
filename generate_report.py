import pandas as pd
from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "olist.db"
SQL_FILE = BASE_DIR / "queries.sql"

def save_excel(df_data,filename):
    with pd.ExcelWriter(filename,engine='openpyxl') as writer:
        for sheet_name,df in df_data.items():
            df.to_excel(writer,sheet_name=sheet_name,index=False)
    print(f"报表已成功保存至 {filename}")


def load_sql(query_name):
# 阅读器
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    tag = f"-- [{query_name}]"
    if tag in content:

        sql_part = content.split(tag)[1]
        if "-- [" in sql_part:
            sql_part = sql_part.split("-- [")[0]
        return sql_part.strip()
    else:
        raise ValueError(f"在 queries.sql 中找不到标签: {query_name}")

def get_gmv_report(conn):
    sql=load_sql("gmv")
    df_gmv_report=pd.read_sql(sql,conn)
    return df_gmv_report

def get_retention_matrix_label(conn):
    sql = load_sql("cd")
    df_retention_matrix_label = pd.read_sql(sql, conn)
    return df_retention_matrix_label

def get_retention_rate(conn):
    sql = load_sql("urr")
    df_retention_rate = pd.read_sql(sql, conn)
    return df_retention_rate

def get_rfm_report(conn):
    sql = load_sql("rfm_summary")
    df_rfm_report = pd.read_sql(sql, conn)
    return df_rfm_report

def main():
    conn = sqlite3.connect(DB_PATH)
    print("正在计算大盘指标...")
    df_gmv=get_gmv_report(conn)
    print("正在计算留存矩阵...")
    df_retention_matrix=get_retention_matrix_label(conn)
    print("正在计算用户留存率...")
    df_retention_rate=get_retention_rate(conn)
    print("正在计算 RFM 模型...")
    df_rfm=get_rfm_report(conn)
    report_data={
        "大盘核心指标": df_gmv,
        "用户留存矩阵":df_retention_matrix,
        "用户留存率":df_retention_rate,
        "用户价值分层": df_rfm
    }
    save_excel(report_data, "电商分析报表.xlsx")
    conn.close()

if __name__ == "__main__":
    main()