import streamlit as st
import pandas as pd
import mplfinance as mpf
import yfinance as yf
import matplotlib.pyplot as plt

# 页面配置
st.set_page_config(
    page_title="A股股票查询工具",
    layout="centered"
)

# CSS和标题（略，保持你之前的样式）

# 加载数据
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

# 初始化session_state变量
for key in ["input_prefix", "input_suffix", "input_name", "search_done", "filtered_df"]:
    if key not in st.session_state:
        if key == "filtered_df":
            st.session_state[key] = pd.DataFrame()
        elif key == "search_done":
            st.session_state[key] = False
        else:
            st.session_state[key] = ""

def clear_inputs():
    st.session_state.input_prefix = ""
    st.session_state.input_suffix = ""
    st.session_state.input_name = ""
    st.session_state.search_done = False
    st.session_state.filtered_df = pd.DataFrame()

# 查询UI
st.markdown('<div class="input-row" style="display:flex; gap:10px;">', unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    st.text_input("股票代码前两位(可不填)", max_chars=2, key="input_prefix")
with col2:
    st.text_input("股票代码后两位(可不填)", max_chars=2, key="input_suffix")
st.markdown('</div>', unsafe_allow_html=True)

st.text_input("股票名称关键词（模糊匹配，字符无序无连续）", key="input_name")

st.markdown('<div class="button-row" style="display:flex; gap:10px;">', unsafe_allow_html=True)
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

if st.session_state.search_done:
    filtered_df = st.session_state.filtered_df

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

        # 选择查看K线图，显示名称但返回code
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

        # 绘制K线图函数
        def plot_k_chart(code):
            # 转换为 yfinance 可识别代码
            yf_code = code + (".SS" if code.startswith("6") else ".SZ")
        
            # 获取最近 1 个月的日线数据
            df = yf.download(yf_code, period="1mo", interval="1d", auto_adjust=True)
        
            if df.empty:
                st.warning("⚠️ 未能获取该股票的历史数据。")
                return
        
            # 确保只包含所需列
            required_cols = ["Open", "High", "Low", "Close", "Volume"]
            df = df[required_cols].copy()
        
            # 转换列类型并移除无法转换的行
            for col in required_cols:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
            df.dropna(inplace=True)
        
            # 再次检查列是否为数值型
            for col in required_cols:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    st.error(f"❌ 列 {col} 含有非数值数据。")
                    st.write(df[col].head())
                    return
        
            # 检查索引是否为日期
            if not isinstance(df.index, pd.DatetimeIndex):
                try:
                    df.index = pd.to_datetime(df.index)
                except Exception as e:
                    st.error(f"❌ 日期索引转换失败：{e}")
                    return
        
            # 成功后绘图
            try:
                fig, _ = mpf.plot(
                    df,
                    type='candle',
                    style='yahoo',
                    volume=True,
                    mav=(5, 10),
                    returnfig=True,
                    figsize=(8, 5)
                )
                st.pyplot(fig)
            except Exception as e:
                st.error(f"📉 绘图失败：{e}")


        if not filtered_df.empty:
            selected_code = filtered_df.iloc[0]["code"]
            plot_k_chart(selected_code)
