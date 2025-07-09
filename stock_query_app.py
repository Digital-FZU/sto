import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# 页面配置
st.set_page_config(
    page_title="A股股票查询工具",
    layout="wide"
)

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
st.markdown('<div class="main-title">📈 A股股票查询工具（实时价格 + 查询时间）</div>', unsafe_allow_html=True)

# 读取股票和ETF数据文件（Excel从GitHub下载）
STOCK_FILE = "A股股票列表.xlsx"
SH_ETF_FILE = "上证ETF列表.xlsx"
SZ_ETF_FILE = "深圳ETF列表.xlsx"

@st.cache_data(show_spinner=False)
def load_data():
    try:
        stock_df = pd.read_excel(STOCK_FILE, dtype=str)
        stock_df = stock_df.rename(columns={"code": "code", "name": "name"})[["code", "name"]]

        sh_etf_df = pd.read_excel(SH_ETF_FILE, dtype=str)
        sz_etf_df = pd.read_excel(SZ_ETF_FILE, dtype=str)
        etf_df = pd.concat([
            sh_etf_df.rename(columns={"证券代码": "code", "证券简称": "name"})[["code", "name"]],
            sz_etf_df.rename(columns={"证券代码": "code", "证券简称": "name"})[["code", "name"]]
        ], ignore_index=True)

        combined_df = pd.concat([stock_df, etf_df], ignore_index=True)
        combined_df["code"] = combined_df["code"].astype(str)
        combined_df["name"] = combined_df["name"].astype(str)

        return combined_df
    except Exception as e:
        st.error(f"❌ 数据读取失败：{e}")
        return pd.DataFrame(columns=["code", "name"])

stock_df = load_data()

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

def get_eastmoney_minute_kline(code: str, market: str, date: str, klt: int = 1):
    secid = f"{market}.{code}"
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "klt": klt,
        "fqt": 0,
        "beg": date,
        "end": date,
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, params=params, headers=headers)
        data = res.json()
        if "data" in data and "klines" in data["data"]:
            raw = data["data"]["klines"]
            df = pd.DataFrame([r.split(",") for r in raw], columns=[
                "时间", "开盘", "收盘", "最高", "最低", "成交量", "成交额", "振幅"])
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

for key in ["input_prefix", "input_suffix", "input_name", "search_done", "filtered_df"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "filtered_df" else pd.DataFrame()

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""
    st.session_state.search_done = False
    st.session_state.filtered_df = pd.DataFrame()

col1, col2 = st.columns(2)
with col1:
    st.text_input("股票代码前两位(可选)", max_chars=2, key="input_prefix")
with col2:
    st.text_input("股票代码后两位(可选)", max_chars=2, key="input_suffix")

st.text_input("股票名称关键词（字符无序、模糊匹配）", key="input_name")

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

        st.success(f"✅ 共找到 {len(filtered_df)} 支符合条件的证券（股票和ETF）：")
        st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

        csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下载结果为 CSV 文件",
            data=csv,
            file_name="查询结果.csv",
            mime="text/csv"
        )

        code_list = filtered_df["code"].tolist()
        name_list = filtered_df["name"].tolist()

        def format_name(code):
            idx = code_list.index(code)
            return f"{name_list[idx]}"

        selected_code = st.selectbox(
            "📊 选择要查看K线图的证券",
            options=code_list,
            format_func=format_name
        )

        if selected_code:
            market = "1" if selected_code.startswith("6") else "0"
            quote_url = f"https://quote.eastmoney.com/{'sh' if market == '1' else 'sz'}{selected_code}.html"

            st.markdown("### 🧭 东方财富网 K 线图")
            st.markdown(
                f"""
                <iframe src="{quote_url}" width="100%" height="600" style="border:none;"></iframe>
                """,
                unsafe_allow_html=True
            )
            st.markdown(
                f'<div style="text-align:center; margin-top:10px;">'
                f'<a href="{quote_url}" target="_blank" style="text-decoration:none;">'
                f'<button style="background-color:#2c3e50; color:white; border:none; padding:10px 20px; border-radius:6px; font-size:16px; cursor:pointer;">🔗 在新标签页中打开</button>'
                f'</a></div>',
                unsafe_allow_html=True
            )

            # 查询指定时间
            with st.expander("⏱ 查询指定时间价格"):
                selected_time = st.time_input("选择时间点（例如09:45）")
                selected_date = datetime.now().strftime("%Y%m%d")
                df_kline = get_eastmoney_minute_kline(selected_code, market, selected_date)
                if not df_kline.empty:
                    match_row = df_kline[df_kline["时间"].str.contains(selected_time.strftime("%H:%M"))]
                    if not match_row.empty:
                        st.dataframe(match_row)
                    else:
                        st.warning("⏳ 未找到该时间点的价格，可能尚未更新或无交易数据。")
                else:
                    st.error("❌ 获取分钟K线失败。")
