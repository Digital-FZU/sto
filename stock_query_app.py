import streamlit as st
import pandas as pd

st.set_page_config(page_title="A股股票代码查询", layout="wide")
st.title("📈 A股股票代码查询工具")

# 默认读取仓库里的 Excel 文件
EXCEL_FILE = "A股股票列表.xlsx"

# 读取数据
@st.cache_data(show_spinner=False)
def load_data():
    try:
        df = pd.read_excel(EXCEL_FILE, dtype={"code": str})
        df["code"] = df["code"].astype(str)
        df["name"] = df["name"].astype(str)
        return df
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        return pd.DataFrame(columns=["code", "name"])

stock_df = load_data()

# 输入筛选条件
prefix = st.text_input("股票代码前两位（可留空）", max_chars=2)
suffix = st.text_input("股票代码后两位（可留空）", max_chars=2)
name_keyword = st.text_input("股票名称关键词（模糊搜索，可留空）")

if st.button("🔍 查询"):
    filtered_df = stock_df

    if prefix:
        filtered_df = filtered_df[filtered_df["code"].str.startswith(prefix)]

    if suffix:
        filtered_df = filtered_df[filtered_df["code"].str.endswith(suffix)]

    if name_keyword:
        filtered_df = filtered_df[filtered_df["name"].str.contains(name_keyword, case=False, na=False)]

    if filtered_df.empty:
        st.warning("未找到符合条件的股票。")
    else:
        st.success(f"共找到 {len(filtered_df)} 条匹配结果：")
        st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

        csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 下载结果为 CSV", data=csv, file_name="股票查询结果.csv", mime="text/csv")
