import pandas as pd
from pathlib import Path
import sqlite3
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "olist.db"
SQL_FILE = BASE_DIR / "queries.sql"

def save_excel(df_data,filename):
    with pd.ExcelWriter(filename,engine='openpyxl') as writer:
        for sheet_name,df in df_data.items():
            df.to_excel(writer,sheet_name=sheet_name,index=False)
            # excel美化
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes = "A2"
            # 2. 设置表头样式（深蓝底、白字、加粗、居中）
            header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            # 3. 自动调整列宽 + 数据居中
            for col in worksheet.columns:
                max_length = 0
                col_letter = col[0].column_letter
                for cell in col:

                    if cell.row > 1:
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    try:
                        if cell.value:
                            val_str = str(cell.value)
                            length = sum(2 if ord(c) > 127 else 1 for c in val_str)
                            if length > max_length:
                                max_length = length
                    except:
                        pass
                adjusted_width = min(max_length + 4, 50)
                worksheet.column_dimensions[col_letter].width = adjusted_width
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