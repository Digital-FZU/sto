import streamlit as st
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="A股股票查询工具",
    layout="centered",
    initial_sidebar_state="auto"
)

# --- 样式部分 ---
st.markdown("""
    <style>
        .main-title {
            font-size: 28px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 25px;
        }

        .row-flex {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }

        .row-flex input {
            flex: 1;
            padding: 10px;
            font-size: 16px;
        }

        .row-buttons {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }

        .row-buttons button {
            flex: 1;
            padding: 10px;
            font-size: 16px;
            cursor: pointer;
        }

        @media screen and (max-width: 600px) {
            .row-flex, .row-buttons {
                flex-direction: row;
            }
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📈 A股股票代码查询工具</div>', unsafe_allow_html=True)

# --- 数据加载 ---
EXCEL_FILE = "A股股票列表.xlsx"

@st.cache_data
def load_data():
    try:
        df = pd.read_excel(EXCEL_FILE, dtype={"code": str})
        df["code"] = df["code"].astype(str)
        df["name"] = df["name"].astype(str)
        return df
    except Exception as e:
        st.error(f"❌ 数据读取失败：{e}")
        return pd.DataFrame(columns=["code", "name"])

stock_df = load_data()

# --- 表单输入 ---
with st.form("search_form"):
    st.markdown("""
        <div class="row-flex">
            <input name="prefix" placeholder="股票代码前两位（如 60）" maxlength="2" />
            <input name="suffix" placeholder="股票代码后两位（如 88）" maxlength="2" />
        </div>
    """, unsafe_allow_html=True)

    name_keyword = st.text_input("股票名称关键词（模糊匹配，字符无序无连续）")

    submitted = st.form_submit_button("🚀 开始查询")
    clear = st.form_submit_button("🧹 清除条件")

# --- 替代旧API：使用 st.query_params ---
prefix = st.query_params.get("prefix", [""])[0]
suffix = st.query_params.get("suffix", [""])[0]

# 兼容状态控制
if "_form_submit" not in st.session_state:
    st.session_state["_form_submit"] = False

if submitted:
    st.session_state["_form_submit"] = True
    prefix = st.query_params.get("prefix", [""])[0]
    suffix = st.query_params.get("suffix", [""])[0]

if clear:
    st.session_state["_form_submit"] = False
    prefix = ""
    suffix = ""
    name_keyword = ""

# --- 模糊匹配函数 ---
def fuzzy_match(name: str, keyword: str) -> bool:
    return all(char in name for char in keyword)

# --- 查询逻辑 ---
if st.session_state["_form_submit"]:
    filtered_df = stock_df.copy()
    if prefix:
        filtered_df = filtered_df[filtered_df["code"].str.startswith(prefix)]
    if suffix:
        filtered_df = filtered_df[filtered_df["code"].str.endswith(suffix)]
    if name_keyword:
        filtered_df = filtered_df[filtered_df["name"].apply(lambda x: fuzzy_match(x, name_keyword))]

    if filtered_df.empty:
        st.warning("😥 没有找到符合条件的股票，请尝试调整关键词。")
    else:
        st.success(f"✅ 共找到 {len(filtered_df)} 支符合条件的股票：")
        st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

        csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 下载结果为 CSV 文件", data=csv, file_name="股票查询结果.csv", mime="text/csv")
