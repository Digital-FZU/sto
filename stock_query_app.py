import streamlit as st
import pandas as pd
import requests
import json

# 页面配置
st.set_page_config(
    page_title="A股股票查询工具",
    layout="centered",
    initial_sidebar_state="auto"
)

# 自定义CSS
st.markdown("""
    <style>
        .main-title {
            font-size: 28px;
            font-weight: 700;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 25px;
            padding-top: 10px;
        }
        .input-row, .button-row {
            display: flex;
            gap: 10px;
            justify-content: space-between;
        }
        .input-col, .button-col {
            flex: 1;
        }
        @media (max-width: 600px) {
            .input-row, .button-row {
                flex-direction: row;
                flex-wrap: nowrap;
            }
        }
        .stTextInput > div > div > input {
            padding: 8px;
            font-size: 16px;
        }
        .stButton > button {
            font-size: 16px;
            padding: 10px 0;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📈 A股股票查询工具</div>', unsafe_allow_html=True)

# 读取 Excel 股票列表
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

# 获取网易财经实时行情（批量）
@st.cache_data(show_spinner=False, ttl=60)
def get_stock_info_from_163(codes: list):
    try:
        query_codes = []
        for code in codes:
            suffix = "0" if code.startswith("6") else "1"
            query_codes.append(code + suffix)

        query_str = ",".join(query_codes)
        url = f"https://api.money.126.net/data/feed/{query_str}?callback=callback"
        res = requests.get(url)
        res.encoding = "utf-8"
        json_str = res.text.strip()[9:-1]
        data = json.loads(json_str)

        stock_info = {}
        for key, val in data.items():
            stock_info[val['code']] = {
                "当前价格": val.get("price"),
                "昨收": val.get("yestclose"),
                "今开": val.get("open"),
                "涨跌额": round(val.get("updown", 0), 2),
                "涨跌幅": f"{val.get('percent', 0.0):.2f}%"
            }
        return stock_info
    except Exception as e:
        st.error(f"❌ 获取实时行情失败：{e}")
        return {}

# 初始化状态
for key in ["input_prefix", "input_suffix", "input_name", "search_done", "filtered_df"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "filtered_df" else pd.DataFrame()

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""
    st.session_state.search_done = False
    st.session_state.filtered_df = pd.DataFrame()

# 输入框
st.markdown('<div class="input-row">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.text_input("股票代码前两位(可不填)", max_chars=2, key="input_prefix")
with col2:
    st.text_input("股票代码后两位(可不填)", max_chars=2, key="input_suffix")
st.markdown('</div>', unsafe_allow_html=True)

st.text_input("股票名称关键词（模糊匹配，字符无序无连续）", key="input_name")

# 按钮
st.markdown('<div class="button-row">', unsafe_allow_html=True)
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    if st.button("🚀 开始查询", use_container_width=True):
        prefix = st.session_state.input_prefix
        suffix = st.session_state.input_suffix
        name_keyword = st.session_state.input_name

        def fuzzy_match(name: str, keyword: str) -> bool:
            return all(char in name for char in keyword)

        filtered_df = stock_df.copy()
        if prefix:
            filtered_df = filtered_df[filtered_df["code"].str.startswith(prefix)]
        if suffix:
            filtered_df = filtered_df[filtered_df["code"].str.endswith(suffix)]
        if name_keyword:
            filtered_df = filtered_df[filtered_df["name"].apply(lambda x: fuzzy_match(x, name_keyword))]

        st.session_state.filtered_df = filtered_df
        st.session_state.search_done = True
with btn_col2:
    st.button("🧹 清除条件", on_click=clear_inputs, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# 查询结果显示
if st.session_state.search_done:
    filtered_df = st.session_state.filtered_df

    if filtered_df.empty:
        st.warning("😥 没有找到符合条件的股票，请尝试调整关键词。")
    else:
        with st.spinner("⏳ 正在获取实时行情..."):
            codes = filtered_df["code"].tolist()
            info_dict = get_stock_info_from_163(codes)

            for col in ["当前价格", "昨收", "今开", "涨跌额", "涨跌幅"]:
                filtered_df[col] = filtered_df["code"].map(lambda x: info_dict.get(x, {}).get(col, None))

        st.success(f"✅ 共找到 {len(filtered_df)} 支符合条件的股票：")
        st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

        csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下载结果为 CSV 文件",
            data=csv,
            file_name="股票查询结果.csv",
            mime="text/csv"
        )

        code_list = filtered_df["code"].tolist()
        name_list = filtered_df["name"].tolist()

        def format_name(code):
            idx = code_list.index(code)
            return f"{name_list[idx]}"

        selected_code = st.selectbox(
            "📊 选择要查看K线图的股票",
            options=code_list,
            format_func=format_name
        )

        def get_k_chart_url(code: str) -> str:
            return f"https://quote.eastmoney.com/{'sh' if code.startswith('6') else 'sz'}{code}.html"

        if selected_code:
            st.markdown("### 📈 当前选中股票的K线图（来自东方财富网）")
            st.components.v1.iframe(get_k_chart_url(selected_code), height=600, scrolling=True)
