import streamlit as st
import pandas as pd
import requests

# 页面配置（宽屏展示）
st.set_page_config(
    page_title="A股股票&ETF查询工具",
    layout="wide"
)

# 页面标题样式
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
    </style>
""", unsafe_allow_html=True)
st.markdown('<div class="main-title">📈 A股股票 & ETF 查询工具（实时价格）</div>', unsafe_allow_html=True)

# 加载股票 + ETF 基础信息
A股_FILE = "A股股票列表.xlsx"
上证ETF_FILE = "上证ETF列表.xlsx"
深证ETF_FILE = "深圳ETF列表.xlsx"

@st.cache_data(show_spinner=False)
def load_all_data():
    try:
        stock_df = pd.read_excel(A股_FILE, dtype={"code": str})
        sz_etf_df = pd.read_excel(深证ETF_FILE, dtype={"证券代码": str})
        sh_etf_df = pd.read_excel(上证ETF_FILE, dtype={"证券代码": str})

        stock_df = stock_df.rename(columns={"code": "code", "name": "name"})[["code", "name"]]
        sz_etf_df = sz_etf_df.rename(columns={"证券代码": "code", "证券简称": "name"})[["code", "name"]]
        sh_etf_df = sh_etf_df.rename(columns={"证券代码": "code", "证券简称": "name"})[["code", "name"]]

        combined_df = pd.concat([stock_df, sz_etf_df, sh_etf_df], ignore_index=True).drop_duplicates(subset="code")
        return combined_df
    except Exception as e:
        st.error(f"❌ 数据读取失败：{e}")
        return pd.DataFrame(columns=["code", "name"])

stock_df = load_all_data()

# 腾讯财经接口（实时价格）
@st.cache_data(show_spinner=False, ttl=60)
def get_stock_info_from_tencent(codes: list):
    try:
        query_codes = ["sh" + c if c.startswith("6") else "sz" + c for c in codes]
        url = "https://qt.gtimg.cn/q=" + ",".join(query_codes)
        res = requests.get(url)
        res.encoding = "gbk"
        lines = res.text.strip().splitlines()

        info_dict = {}
        for line in lines:
            try:
                code_key = line.split("=")[0].split("_")[-1][2:]
                data = line.split("~")
                info_dict[code_key] = {
                    "当前价格": float(data[3]),
                    "昨收": float(data[4]),
                    "今开": float(data[5]),
                    "涨跌额": round(float(data[3]) - float(data[4]), 2),
                    "涨跌幅": f"{(float(data[3]) - float(data[4])) / float(data[4]) * 100:.2f}%",
                }
            except Exception:
                continue
        return info_dict
    except Exception as e:
        st.error(f"❌ 获取实时行情失败：{e}")
        return {}

# Session state 初始化
for key in ["input_prefix", "input_suffix", "input_name", "search_done", "filtered_df"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "filtered_df" else pd.DataFrame()

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""
    st.session_state.search_done = False
    st.session_state.filtered_df = pd.DataFrame()

# 输入区
col1, col2 = st.columns(2)
with col1:
    st.text_input("股票/ETF 代码前两位(可选)", max_chars=2, key="input_prefix")
with col2:
    st.text_input("股票/ETF 代码后两位(可选)", max_chars=2, key="input_suffix")

st.text_input("名称关键词（字符无序、模糊匹配）", key="input_name")

# 查询 & 清除按钮
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

# 显示查询结果
if st.session_state.search_done:
    filtered_df = st.session_state.filtered_df

    if filtered_df.empty:
        st.warning("😥 没有找到符合条件的股票或ETF，请尝试调整关键词。")
    else:
        with st.spinner("⏳ 正在获取实时行情..."):
            codes = filtered_df["code"].tolist()
            info_dict = get_stock_info_from_tencent(codes)

            for col in ["当前价格", "昨收", "今开", "涨跌额", "涨跌幅"]:
                filtered_df[col] = filtered_df["code"].map(lambda x: info_dict.get(x, {}).get(col, None))

        st.success(f"✅ 共找到 {len(filtered_df)} 条符合条件的记录：")
        st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

        # 下载按钮
        csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下载结果为 CSV 文件",
            data=csv,
            file_name="查询结果.csv",
            mime="text/csv"
        )

        # 可选展示 K 线图
        code_list = filtered_df["code"].tolist()
        name_list = filtered_df["name"].tolist()

        def format_name(code):
            idx = code_list.index(code)
            return f"{name_list[idx]}"

        selected_code = st.selectbox(
            "📊 选择要查看K线图的股票或ETF",
            options=code_list,
            format_func=format_name
        )

        def get_k_chart_url(code: str) -> str:
            return f"https://quote.eastmoney.com/{'sh' if code.startswith('6') else 'sz'}{code}.html"

        if selected_code:
            st.markdown("### 📈 当前选中股票/ETF 的 K 线图（来自东方财富网）")

            chart_url = get_k_chart_url(selected_code)
            st.components.v1.iframe(chart_url, height=600, width="100%", scrolling=True)

            st.markdown(f"""
                <div style='text-align: right; margin-top: 10px;'>
                    <a href="{chart_url}" target="_blank" style="text-decoration: none;">
                        <button style="
                            background-color: #2c7be5;
                            color: white;
                            padding: 6px 12px;
                            border: none;
                            border-radius: 5px;
                            cursor: pointer;
                        ">
                            🔗 在新标签页中打开
                        </button>
                    </a>
                </div>
            """, unsafe_allow_html=True)
