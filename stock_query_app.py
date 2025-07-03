import streamlit as st
import pandas as pd

# 页面配置
st.set_page_config(
    page_title="A股股票查询工具",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": None
    }
)

# 页面样式和标题
st.markdown("""
    <style>
        .main-title {
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 20px;
        }
        .footer {
            text-align: center;
            font-size: 13px;
            color: gray;
            margin-top: 50px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📈 A股股票代码查询工具</div>', unsafe_allow_html=True)

# --- 加载数据 ---
EXCEL_FILE = "A股股票列表.xlsx"

@st.cache_data(show_spinner=False)
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

# ---- 初始化 session_state 避免赋值时报错 ----
for key in ["input_prefix", "input_suffix", "input_name"]:
    if key not in st.session_state:
        st.session_state[key] = ""

# 清除输入的回调函数
def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""

# --- 查询输入区域 ---
with st.container():
    st.markdown("### 🔎 查询条件")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.text_input("股票代码前两位", max_chars=2, key="input_prefix")
    with col2:
        st.text_input("股票代码后两位", max_chars=2, key="input_suffix")
    with col3:
        st.text_input("股票名称关键词", key="input_name")

    col4, col5 = st.columns([1, 1])
    with col4:
        search_btn = st.button("🚀 开始查询")
    with col5:
        clear_btn = st.button("🧹 清除查询条件", on_click=clear_inputs)

# --- 获取输入值 ---
prefix = st.session_state["input_prefix"]
suffix = st.session_state["input_suffix"]
name_keyword = st.session_state["input_name"]

# --- 查询逻辑 ---
if search_btn:
    filtered_df = stock_df.copy()

    if prefix:
        filtered_df = filtered_df[filtered_df["code"].str.startswith(prefix)]
    if suffix:
        filtered_df = filtered_df[filtered_df["code"].str.endswith(suffix)]
    if name_keyword:
        filtered_df = filtered_df[filtered_df["name"].str.contains(name_keyword, case=False, na=False)]

    if filtered_df.empty:
        st.warning("😥 没有找到符合条件的股票，请尝试调整关键词。")
    else:
        st.success(f"✅ 共找到 {len(filtered_df)} 支符合条件的股票：")
        st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

        csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下载结果为 CSV 文件",
            data=csv,
            file_name="股票查询结果.csv",
            mime="text/csv"
        )

# 页脚
#st.markdown('<div class="footer">© 2025 A股查询工具 by 你自己 | Powered by Streamlit</div>', unsafe_allow_html=True)
