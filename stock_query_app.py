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

# 自定义CSS美化和响应式布局
st.markdown("""
    <style>
        /* 主标题 */
        .main-title {
            font-size: 28px;
            font-weight: 700;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 25px;
            padding-top: 10px;
        }
        /* 输入框宽度自适应 */
        input[type="text"] {
            width: 100% !important;
            box-sizing: border-box;
            font-size: 16px !important;
            padding: 8px 10px !important;
            margin-bottom: 12px !important;
        }
        /* 按钮宽度满屏，底部间距 */
        div.stButton > button {
            font-size: 16px;
            padding: 10px 0;
        }
        /* 页脚字体大小 */
        .footer {
            text-align: center;
            font-size: 12px;
            color: gray;
            margin-top: 40px;
        }
        /* 响应式输入与按钮在移动端整齐显示 */
        .block-container .stTextInput, .block-container .stButton {
            margin-bottom: 10px;
        }
        @media only screen and (max-width: 600px) {
            .stTextInput > div, .stButton {
                width: 100% !important;
            }
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

# 初始化 session_state
for key in ["input_prefix", "input_suffix", "input_name"]:
    if key not in st.session_state:
        st.session_state[key] = ""

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""

# 查询条件区域（紧凑排列）
col1, col2 = st.columns(2)
with col1:
    st.text_input("代码前两位（可不填）", max_chars=2, key="input_prefix", help="例如 60、00、30 等")
with col2:
    st.text_input("代码后两位（可不填）", max_chars=2, key="input_suffix", help="例如 01、88、25 等")

st.text_input("股票名称关键词（模糊匹配，字符无序无连续）", key="input_name")

# 查询与清除按钮（同一行）
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    search_btn = st.button("🚀 开始查询", use_container_width=True)
with col_btn2:
    st.button("🧹 清除条件", on_click=clear_inputs, use_container_width=True)

# 获取输入值
prefix = st.session_state["input_prefix"]
suffix = st.session_state["input_suffix"]
name_keyword = st.session_state["input_name"]

# 模糊匹配函数
def fuzzy_match(name: str, keyword: str) -> bool:
    return all(char in name for char in keyword)

# 查询逻辑
if search_btn:
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
        st.download_button(
            label="📥 下载结果为 CSV 文件",
            data=csv,
            file_name="股票查询结果.csv",
            mime="text/csv"
        )

# 页脚（可启用）
# st.markdown('<div class="footer">© 2025 A股查询工具 | Powered by Streamlit</div>', unsafe_allow_html=True)
