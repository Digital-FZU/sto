import streamlit as st
import pandas as pd
import akshare as ak
import os

st.set_page_config(page_title="A股股票代码查询", layout="wide")
st.title("📈 A股股票代码查询工具（增强版）")

# --- 数据源选择 ---
st.sidebar.header("数据源设置")
data_source = st.sidebar.radio("选择数据来源：", ["线上查询（akshare）", "本地文件上传"])

# 如果本地上传，提供文件上传控件
uploaded_file = None
if "本地" in data_source:
    uploaded_file = st.sidebar.file_uploader("上传 A股股票列表.xlsx", type=["xlsx"])

# --- 输入查询条件 ---
st.sidebar.header("筛选条件")
prefix = st.sidebar.text_input("股票代码前两位（可留空）", max_chars=2)
suffix = st.sidebar.text_input("股票代码后两位（可留空）", max_chars=2)
name_keyword = st.sidebar.text_input("股票名称关键词（模糊搜索）")

# 查询按钮
query_triggered = st.sidebar.button("🔍 查询")

# --- 查询逻辑 ---
if query_triggered:
    try:
        # 数据读取
        if "线上" in data_source:
            stock_df = ak.stock_info_a_code_name()
        else:
            if uploaded_file is None:
                st.error("请先上传包含股票代码的 Excel 文件。")
                st.stop()
            stock_df = pd.read_excel(uploaded_file, dtype={"code": str})

        # 确保 code 是字符串类型
        stock_df["code"] = stock_df["code"].astype(str)
        stock_df["name"] = stock_df["name"].astype(str)

        # --- 条件过滤 ---
        filtered_df = stock_df.copy()

        if prefix:
            filtered_df = filtered_df[filtered_df["code"].str.startswith(prefix)]
        if suffix:
            filtered_df = filtered_df[filtered_df["code"].str.endswith(suffix)]
        if name_keyword:
            filtered_df = filtered_df[filtered_df["name"].str.contains(name_keyword, case=False, na=False)]

        # --- 显示结果 ---
        if filtered_df.empty:
            st.warning("未找到符合条件的股票。请调整筛选条件。")
        else:
            st.success(f"共找到 {len(filtered_df)} 条匹配结果：")
            st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

            # 下载按钮
            csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 下载结果为 CSV",
                data=csv,
                file_name="股票查询结果.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"出错了：{e}")
