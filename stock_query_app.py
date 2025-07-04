import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

# 页面配置
st.set_page_config(
    page_title="A股股票查询工具",
    layout="centered",
    initial_sidebar_state="auto"
)

# 样式
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
}
.input-col, .button-col {
    flex: 1;
}
.stTextInput > div > div > input {
    padding: 8px;
    font-size: 16px;
}
.stButton > button {
    font-size: 16px;
    padding: 10px 0;
}
@media (max-width: 600px) {
    .input-row, .button-row {
        flex-direction: row;
        flex-wrap: nowrap;
    }
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📈 A股股票代码查询工具</div>', unsafe_allow_html=True)

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

# 初始化session_state
for key in ["input_prefix", "input_suffix", "input_name", "selected_stock"]:
    if key not in st.session_state:
        st.session_state[key] = ""

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""
    st.session_state.selected_stock = ""

# 输入框排一行
st.markdown('<div class="input-row">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.text_input("股票代码前两位(可不填)", max_chars=2, key="input_prefix")
with col2:
    st.text_input("股票代码后两位(可不填)", max_chars=2, key="input_suffix")
st.markdown('</div>', unsafe_allow_html=True)

# 名称关键词输入
st.text_input("股票名称关键词（模糊匹配，字符无序无连续）", key="input_name")

# 按钮排一行
st.markdown('<div class="button-row">', unsafe_allow_html=True)
btn_col1, btn_col2 = st.columns(2)
with btn_col1:
    search_btn = st.button("🚀 开始查询", use_container_width=True)
with btn_col2:
    st.button("🧹 清除条件", on_click=clear_inputs, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

prefix = st.session_state.input_prefix
suffix = st.session_state.input_suffix
name_keyword = st.session_state.input_name

def fuzzy_match(name: str, keyword: str) -> bool:
    return all(char in name for char in keyword)

# 查询结果和选择框
filtered_df = pd.DataFrame()
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
else:
    # 如果没点击查询，则显示空表，防止报错
    filtered_df = pd.DataFrame(columns=stock_df.columns)

# 选择股票（显示名称，value是code）
# 过滤后的股票列表，名字和代码组成元组列表
options = list(zip(filtered_df["name"], filtered_df["code"]))

if options:
    # 显示selectbox，显示股票名称，返回(name, code)元组
    selected = st.selectbox(
        "选择要查看K线图的股票",
        options=options,
        format_func=lambda x: x[0]
    )
    selected_name, selected_code = selected
else:
    st.info("😥 没有符合条件的股票，无法选择查看K线图。")
    selected_name, selected_code = None, None


# K线图绘制函数，使用Plotly
def plot_k_chart_plotly(stock_code):
    if not stock_code:
        return
    try:
        if stock_code.startswith(("0", "3")):
            ticker = f"{stock_code}.SZ"
        elif stock_code.startswith("6"):
            ticker = f"{stock_code}.SS"
        else:
            ticker = stock_code

        df = yf.download(ticker, period="3mo", interval="1d")
        if df.empty:
            st.error("⚠️ 无法获取历史行情数据")
            return

        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Date"])

        fig = go.Figure(data=[go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color='red',
            decreasing_line_color='green',
            name='k线'
        )])

        fig.update_layout(
            title=f"{stock_code} 最近3个月K线图",
            xaxis_title="日期",
            yaxis_title="价格",
            xaxis_rangeslider_visible=False
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"📛 K线图绘制失败: {e}")

if selected_code:
    plot_k_chart_plotly(selected_code)
