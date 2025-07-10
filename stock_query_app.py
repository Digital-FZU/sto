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

for key in ["input_prefix", "input_suffix", "input_name", "search_done", "filtered_df"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key != "filtered_df" else pd.DataFrame()

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""
    st.session_state.query_time_input = ""  
    st.session_state.search_done = False
    st.session_state.filtered_df = pd.DataFrame()

col1, col2 = st.columns(2)
with col1:
    st.text_input("股票代码前两位(可选)", max_chars=2, key="input_prefix")
with col2:
    st.text_input("股票代码后两位(可选)", max_chars=2, key="input_suffix")

st.text_input("股票名称关键词（字符无序、模糊匹配）", key="input_name")

# 新增：指定查询时间点输入
query_time_input = st.text_input("指定查询时间点（格式 HH:MM，选填）", value="")

btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    if st.button("🚀 开始查询", use_container_width=True):
        prefix = st.session_state.input_prefix
        suffix = st.session_state.input_suffix
        name_keyword = st.session_state.input_name
        query_time = query_time_input.strip()

        def fuzzy_match(name: str, keyword: str) -> bool:
            return all(char in name for char in keyword)

        filtered_df = stock_df.copy()
        if prefix:
            filtered_df = filtered_df[filtered_df["code"].str.startswith(prefix)]
        if suffix:
            filtered_df = filtered_df[filtered_df["code"].str.endswith(suffix)]
        if name_keyword:
            filtered_df = filtered_df[filtered_df["name"].apply(lambda x: fuzzy_match(x, name_keyword))]

        codes = filtered_df["code"].tolist()

        # 获取腾讯实时行情
        info_dict = get_stock_info_from_tencent(codes)
        for col in ["当前价格", "昨收", "今开", "涨跌额", "涨跌幅"]:
            filtered_df[col] = filtered_df["code"].map(lambda x: info_dict.get(x, {}).get(col, None))

        # 判断时间格式和是否在开盘时段
        def is_valid_time(t):
            try:
                datetime.strptime(t, "%H:%M")
                return (("09:30" <= t <= "11:30") or ("13:00" <= t <= "15:00"))
            except:
                return False

        if query_time and is_valid_time(query_time):
            prices_at_time = {}
            today_str = datetime.today().strftime("%Y%m%d")
            for code in codes:
                market = "1" if code.startswith("6") else "0"
                secid = f"{market}.{code}"
                params = {
                    "secid": secid,
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56",
                    "klt": 1,
                    "fqt": 1,
                    "beg": today_str,
                    "end": today_str,
                }
                try:
                    resp = requests.get("https://push2his.eastmoney.com/api/qt/stock/kline/get", params=params).json()
                    klines = resp.get("data", {}).get("klines", [])
                    matched = [k for k in klines if k.split(",")[0].endswith(query_time)]
                    if matched:
                        prices_at_time[code] = matched[0].split(",")[2]  # 收盘价
                    else:
                        prices_at_time[code] = None
                except:
                    prices_at_time[code] = None
            filtered_df["指定时间价格"] = filtered_df["code"].map(lambda c: prices_at_time.get(c))
        else:
            filtered_df["指定时间价格"] = None

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
            # （实时行情已查询并存储，无需重复获取）
            pass

        st.success(f"✅ 共找到 {len(filtered_df)} 支符合条件的证券（股票和ETF）：")
        #st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)
        st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True, height=700)


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

            # 保留原有单个时间点查询功能（非必需，留着也无害）
            st.markdown("### ⏱️ 查询指定时间点价格（仅支持当日分钟K线）")
            query_time = st.text_input("请输入时间（如 09:45）：", value="09:45")
            query_btn = st.button("🔍 查询指定时间点价格")

            if query_btn:
                try:
                    datetime.strptime(query_time, "%H:%M")
                    if not (("09:30" <= query_time <= "11:30") or ("13:00" <= query_time <= "15:00")):
                        st.warning("⏰ 时间不在开盘时段（09:30–11:30, 13:00–15:00）")
                    else:
                        secid = f"{'1' if selected_code.startswith('6') else '0'}.{selected_code}"
                        today_str = datetime.today().strftime("%Y%m%d")
                        kline_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                        params = {
                            "secid": secid,
                            "fields1": "f1,f2,f3,f4,f5,f6",
                            "fields2": "f51,f52,f53,f54,f55,f56",
                            "klt": 1,
                            "fqt": 1,
                            "beg": today_str,
                            "end": today_str,
                        }
                        resp = requests.get(kline_url, params=params).json()
                        if "data" in resp and "klines" in resp["data"]:
                            match = [k for k in resp["data"]["klines"] if k.split(",")[0].endswith(query_time)]
                            if match:
                                time_data = match[0].split(",")
                                price = time_data[2]
                                st.success(f"✅ {query_time} 的价格为：¥ {price}")
                            else:
                                st.warning("未找到该时间点的数据")
                        else:
                            st.error("❌ 获取K线数据失败")
                except ValueError:
                    st.error("⚠️ 时间格式错误，应为 HH:MM")
