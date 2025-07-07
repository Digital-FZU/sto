import streamlit as st
import pandas as pd
import akshare as ak
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from collections import defaultdict
import os
import matplotlib.font_manager as fm

# ----------------------------
# 设置中文字体（NotoSansSC-Regular.otf）
# ----------------------------
def set_chinese_font():
    font_path = os.path.join(os.path.dirname(__file__), "NotoSansSC-Light.ttf")
    if os.path.exists(font_path):
        font_prop = fm.FontProperties(fname=font_path)
        plt.rcParams['font.family'] = font_prop.get_name()
        st.session_state['font_loaded'] = True
    else:
        st.session_state['font_loaded'] = False
        st.warning("⚠️ 中文字体文件未找到，可能中文显示异常。请确保 NotoSansSC-Light.ttfNotoSansSC-Regular.otf 在项目根目录。")

set_chinese_font()

# ----------------------------
# 页面设置
# ----------------------------
st.set_page_config(
    page_title="题材强度热力图",
    layout="wide"
)

st.title("🔥 最近一个月概念题材强度热力图")

# ----------------------------
# 获取数据函数
# ----------------------------
@st.cache_data(show_spinner=True)
def get_concept_heatmap(days=30):
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days + 10)  # 多取几天避开节假日
    date_range = pd.date_range(start=start_date, end=end_date, freq="B")  # B = 工作日

    date_industry_count = defaultdict(lambda: defaultdict(int))
    failed_dates = []

    for date in date_range:
        date_str = date.strftime("%Y%m%d")
        try:
            df = ak.stock_zt_pool_em(date=date_str)
            if "所属行业" not in df.columns or df["所属行业"].isnull().all():
                continue
            counts = df["所属行业"].value_counts()
            for industry, cnt in counts.items():
                date_industry_count[date.strftime("%Y-%m-%d")][industry] = cnt
        except Exception:
            failed_dates.append(date_str)

    df_heat = pd.DataFrame(date_industry_count).T.fillna(0).astype(int).sort_index()
    df_heat = df_heat.loc[:, df_heat.sum() > 5]  # 只显示活跃题材
    return df_heat

# ----------------------------
# 主逻辑
# ----------------------------
heatmap_df = get_concept_heatmap(days=30)

if heatmap_df.empty:
    st.error("⚠️ 未能获取题材强度数据，请稍后重试。")
else:
    st.success(f"✅ 数据加载成功，共包含 {heatmap_df.shape[1]} 个题材")

    # 绘图
    fig, ax = plt.subplots(figsize=(16, 10))
    sns.heatmap(
        heatmap_df.T,
        cmap="YlGnBu",
        linewidths=0.5,
        linecolor="gray",
        ax=ax
    )

    ax.set_title("涨停行业轮动热力图", fontsize=16)
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("所属行业", fontsize=12)
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)
    plt.tight_layout()

    st.pyplot(fig)
