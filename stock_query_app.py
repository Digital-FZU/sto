import streamlit as st
import pandas as pd
import requests

# 页面配置
st.set_page_config(page_title="A股股票/ETF查询工具", layout="centered")

# 页面标题
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

# 文件路径
STOCK_FILE = "A股股票列表.xlsx"
ETF_FILE_SH = "上证ETF列表.xlsx"
ETF_FILE_SZ = "深圳ETF列表.xlsx"

@st.cache_data(show_spinner=False)
def load_data():
    try:
        # 股票数据
        stock_df = pd.read_excel(STOCK_FILE, dtype=str)
        stock_df = stock_df[["code", "name"]]
        stock_df["type"] = "股票"

        # ETF 数据
        etf_sh = pd.read_excel(ETF_FILE_SH, dtype=str)
        etf_sz = pd.read_excel(ETF_FILE_SZ, dtype=str)
        etf_df = pd.concat([etf_sh, etf_sz], ignore_index=True)
        etf_df.columns = ["code", "name"]  # 确保列名一致
        etf_df["type"] = "ETF"

        # 合并
        combined_df = pd.concat([stock_df, etf_df], ignore_index=True)
        combined_df["code"] = combined_df["code"].astype(str).str.zfill(6)
        combined_df["name"] = combined_df["name"].astype(str)
        return combined_df
    except Exception as e:
        st.error(f"❌ 数据读取失败：{e}")
        return pd.DataFrame(columns=["code", "name", "type"])

df_all = load_data()

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
                    "涨跌幅": f"{(float(data[3]) - float(data[4]) ) / float(data[4]) * 100:.2f}%",
                }
            except:
                continue
        return info_dict
    except Exception as e:
        st.error(f"❌ 获取实时行情失败：{e}")
        return {}

# 初始化 Session State
for key in ["input_prefix", "input_suffix", "input_name", "search_done", "filtered_df"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "filtered_df" else pd.DataFrame()

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""
    st.session_state.search_done = False
    st.session_state.filtered_df = pd.DataFrame()

# 输入区域
col1, col2 = st.columns(2)
with col1:
    st.text_input("证券代码前两位(可选)", max_chars=2, key="input_prefix")
with col2:
    st.text_input("证券代码后两位(可选)", max_chars=2, key="input_suffix")

st.text_input("证券名称关键词（字符无序、模糊匹配）", key="input_name")

# 查询和清除
btn1, btn2 = st.columns(2)
with btn1:
    if st.button("🔍 查询", use_container_width=True):
        prefix = st.session_state.input_prefix
        suffix = st.session_state.input_suffix
        keyword = st.session_state.input_name

        def fuzzy_match(name: str, keyword: str) -> bool:
            return all(c in name for c in keyword)

        filtered_df = df_all.copy()
        if prefix:
            filtered_df = filtered_df[filtered_df["code"].str.startswith(prefix)]
        if suffix:
            filtered_df = filtered_df[filtered_df["code"].str.endswith(suffix)]
        if keyword:
            filtered_df = filtered_df[filtered_df["name"].apply(lambda x: fuzzy_match(x, keyword))]

        st.session_state.filtered_df = filtered_df
        st.session_state.search_done = True

with btn2:
    st.button("🧹 清空条件", on_click=clear_inputs, use_container_width=True)

# 显示查询结果
if st.session_state.search_done:
    result_df = st.session_state.filtered_df

    if result_df.empty:
        st.warning("😥 没找到符合条件的证券，请尝试调整查询。")
    else:
        with st.spinner("📡 正在获取实时行情..."):
            codes = result_df["code"].tolist()
            info_dict = get_stock_info_from_tencent(codes)

            # 添加实时行情列
            for col in ["当前价格", "昨收", "今开", "涨跌额", "涨跌幅"]:
                result_df[col] = result_df["code"].map(lambda x: info_dict.get(x, {}).get(col))

        st.success(f"✅ 共找到 {len(result_df)} 支证券（含股票与 ETF）：")
        st.dataframe(result_df.reset_index(drop=True), use_container_width=True)

        # 下载按钮
        csv = result_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下载结果 CSV",
            data=csv,
            file_name="证券查询结果.csv",
            mime="text/csv"
        )

        # K线图选择器
        code_list = result_df["code"].tolist()
        name_list = result_df["name"].tolist()

        def format_label(code):
            return f"{name_list[code_list.index(code)]}（{code}）"

        selected_code = st.selectbox("📊 查看K线图", options=code_list, format_func=format_label)

        if selected_code:
            market = "sh" if selected_code.startswith("6") else "sz"
            st.markdown("### 🧭 东方财富网 K 线图")
            st.components.v1.iframe(f"https://quote.eastmoney.com/{market}{selected_code}.html", height=600, scrolling=True)
