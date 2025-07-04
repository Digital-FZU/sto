import streamlit as st
import pandas as pd
import yfinance as yf
import mplfinance as mpf

# 页面配置
st.set_page_config(
    page_title="A股股票查询工具",
    layout="centered",
    initial_sidebar_state="auto"
)

# 自定义 CSS 样式
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
for key in ["input_prefix", "input_suffix", "input_name", "selected_code"]:
    if key not in st.session_state:
        st.session_state[key] = ""

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""
    st.session_state.selected_code = ""

# 横向输入框
col1, col2 = st.columns(2)
with col1:
    st.text_input("股票代码前两位(可不填)", max_chars=2, key="input_prefix")
with col2:
    st.text_input("股票代码后两位(可不填)", max_chars=2, key="input_suffix")

st.text_input("股票名称关键词（模糊匹配，字符无序无连续）", key="input_name")

# 横向按钮
btn1, btn2 = st.columns(2)
with btn1:
    search_btn = st.button("🚀 开始查询", use_container_width=True)
with btn2:
    st.button("🧹 清除条件", on_click=clear_inputs, use_container_width=True)

# 模糊匹配
def fuzzy_match(name: str, keyword: str) -> bool:
    return all(char in name for char in keyword)

# 查询逻辑
if search_btn:
    df = stock_df.copy()

    if st.session_state.input_prefix:
        df = df[df["code"].str.startswith(st.session_state.input_prefix)]
    if st.session_state.input_suffix:
        df = df[df["code"].str.endswith(st.session_state.input_suffix)]
    if st.session_state.input_name:
        df = df[df["name"].apply(lambda x: fuzzy_match(x, st.session_state.input_name))]

    if df.empty:
        st.warning("😥 没有找到符合条件的股票，请尝试调整关键词。")
    else:
        st.success(f"✅ 共找到 {len(df)} 支符合条件的股票：")
        st.dataframe(df.reset_index(drop=True), use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下载结果为 CSV 文件",
            data=csv,
            file_name="股票查询结果.csv",
            mime="text/csv"
        )

        # 设置默认选中第一支股票的 code
        st.session_state.selected_code = df.iloc[0]["code"]

        # 生成下拉选择（显示股票名称）
        stock_options = df["name"] + "（" + df["code"] + "）"
        name_code_map = dict(zip(stock_options, df["code"]))

        selected_name = st.selectbox(
            "选择要查看K线图的股票：", 
            options=stock_options,
            index=0,
            key="selected_name"
        )
        selected_code = name_code_map[selected_name]

        # 画K线图
        def plot_k_chart(stock_code):
            try:
                # 添加后缀
                ticker = f"{stock_code}.SZ" if stock_code.startswith(("0", "3")) else f"{stock_code}.SS"
                df = yf.download(ticker, period="3mo", interval="1d")

                if df.empty:
                    st.error("⚠️ 无法获取该股票的历史数据，可能是代码无效或无数据。")
                    return

                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

                # 保证所有数据是数值类型
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df.dropna(inplace=True)

                # 画图
                fig, _ = mpf.plot(
                    df,
                    type="candle",
                    style="yahoo",
                    volume=True,
                    mav=(5, 10),
                    returnfig=True
                )
                st.pyplot(fig)

            except Exception as e:
                st.error(f"📛 K线图绘制失败: {e}")

        st.markdown("---")
        st.subheader("📊 K线图展示")
        plot_k_chart(selected_code)
