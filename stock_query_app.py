import streamlit as st
import pandas as pd
import requests
import akshare as ak
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import defaultdict
import platform
import matplotlib

# 页面配置
st.set_page_config(
    page_title="A股股票查询工具",
    layout="centered"
)

# 设置中文字体（跨平台）
def set_chinese_font():
    system = platform.system()
    if system == 'Windows':
        matplotlib.rcParams['font.family'] = 'SimHei'
    elif system == 'Darwin':
        matplotlib.rcParams['font.family'] = 'STHeiti'
    else:
        matplotlib.rcParams['font.family'] = 'DejaVu Sans'
    matplotlib.rcParams['axes.unicode_minus'] = False

set_chinese_font()

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
st.markdown('<div class="main-title">📈 A股股票查询工具（实时价格）</div>', unsafe_allow_html=True)

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

# 输入管理
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
        st.warning("😥 没有找到符合条件的股票，请尝试调整关键词。")
    else:
        with st.spinner("⏳ 正在获取实时行情..."):
            codes = filtered_df["code"].tolist()
            info_dict = get_stock_info_from_tencent(codes)
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

# 🔥 最近一个月概念题材强度热力图
st.markdown("## 🔥 最近一个月涨停题材强度热力图")

@st.cache_data(show_spinner=False)
def get_industry_heatmap_df(days=30):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days + 30)  # 多抓几天确保有交易日
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')

    date_industry_count = defaultdict(lambda: defaultdict(int))
    for date in date_range:
        try:
            df = ak.stock_zt_pool_em(date=date.strftime('%Y%m%d'))
            if '所属行业' not in df.columns or df['所属行业'].isnull().all():
                continue
            counts = df['所属行业'].value_counts()
            for industry, cnt in counts.items():
                date_industry_count[date.strftime('%Y-%m-%d')][industry] = cnt
        except:
            continue

    df_industry = pd.DataFrame(date_industry_count).T.fillna(0).astype(int).sort_index()
    df_industry = df_industry.loc[:, (df_industry.sum(axis=0) > 5)]
    return df_industry

try:
    df_industry = get_industry_heatmap_df(days=30)
    if not df_industry.empty:
        fig = plt.figure(figsize=(16, 10))
        sns.heatmap(df_industry.T, cmap='YlGnBu', linewidths=.5, linecolor='gray')
        plt.title('涨停行业轮动热力图')
        plt.ylabel('所属行业')
        plt.xlabel('日期')
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.warning("⚠️ 未获取到有效的题材热力图数据。")
except Exception as e:
    st.error(f"⚠️ 热力图绘制失败：{e}")
