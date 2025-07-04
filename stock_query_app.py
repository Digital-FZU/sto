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

# 样式
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
    /* 横向输入容器 */
    .input-row, .button-row {
        display: flex;
        gap: 10px;
        flex-wrap: nowrap;
        justify-content: space-between;
    }
    .input-col, .button-col {
        flex: 1;
    }
    /* 按钮和输入框字体大小和内边距 */
    .stTextInput > div > div > input {
        padding: 8px;
        font-size: 16px;
    }
    .stButton > button {
        font-size: 16px;
        padding: 10px 0;
        width: 100%;
    }
    /* 小屏幕竖屏强制两列并排 */
    @media (max-width: 600px) {
        .input-row, .button-row {
            flex-wrap: nowrap !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📈 A股股票代码查询工具</div>', unsafe_allow_html=True)

# --- 加载股票列表 ---
EXCEL_FILE = "A股股票列表.xlsx"

@st.cache_data(show_spinner=False)
def load_stock_list():
    try:
        df = pd.read_excel(EXCEL_FILE, dtype={"code": str})
        df["code"] = df["code"].astype(str)
        df["name"] = df["name"].astype(str)
        return df
    except Exception as e:
        st.error(f"❌ 股票列表加载失败：{e}")
        return pd.DataFrame(columns=["code", "name"])

stock_df = load_stock_list()

# 初始化 session_state
for key in ["input_prefix", "input_suffix", "input_name"]:
    if key not in st.session_state:
        st.session_state[key] = ""

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""

# 横向输入
st.markdown('<div class="input-row">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.text_input("股票代码前两位(可不填)", max_chars=2, key="input_prefix")
with col2:
    st.text_input("股票代码后两位(可不填)", max_chars=2, key="input_suffix")
st.markdown('</div>', unsafe_allow_html=True)

# 名称关键词
st.text_input("股票名称关键词（模糊匹配，无序）", key="input_name")

# 横向按钮
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

# 查询结果
filtered_df = stock_df.copy()
if prefix:
    filtered_df = filtered_df[filtered_df["code"].str.startswith(prefix)]
if suffix:
    filtered_df = filtered_df[filtered_df["code"].str.endswith(suffix)]
if name_keyword:
    filtered_df = filtered_df[filtered_df["name"].apply(lambda x: fuzzy_match(x, name_keyword))]

if search_btn:
    if filtered_df.empty:
        st.warning("😥 没有找到符合条件的股票，请调整关键词")
    else:
        st.success(f"✅ 共找到 {len(filtered_df)} 支股票：")
        st.dataframe(filtered_df.reset_index(drop=True), use_container_width=True)

        csv = filtered_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="📥 下载结果 CSV 文件",
            data=csv,
            file_name="股票查询结果.csv",
            mime="text/csv"
        )

        st.markdown("---")
        st.markdown("### 🕵️ 选择要查看K线图的股票")

        options = {f"{row['name']}（{row['code']}）": row["code"] for _, row in filtered_df.iterrows()}
        selected_name = st.selectbox("选择股票", list(options.keys()))
        selected_code = options[selected_name]

        def plot_k_chart(stock_code):
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

                st.write(df.dtypes)
                st.write(df.head())
                
                # 只保留必须列
                required_cols = ["Open", "High", "Low", "Close", "Volume"]
                df = df[required_cols].copy()
        
                # 转换为数字，并剔除有缺失的行
                for col in required_cols:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df.dropna(subset=required_cols, inplace=True)

                st.write(df.dtypes)
                st.write(df.head())
                # 再确认类型
                if not all(pd.api.types.is_numeric_dtype(df[col]) for col in required_cols):
                    st.error("📛 数据转换失败：有非数字列")
                    return

                st.write(df.dtypes)
                st.write(df.head())
                
                if df.empty:
                    st.error("📛 有效数据为空，无法绘图")
                    return

                fig, axlist = mpf.plot(df, type="candle", style="yahoo",
                                       volume=True, mav=(5, 10), returnfig=True)
                st.pyplot(fig)


            except Exception as e:
                st.error(f"📛 K线图绘制失败: {e}")

        plot_k_chart(selected_code)
