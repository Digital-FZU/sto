import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import pandas as pd
import akshare as ak
import os

def query_stock():
    prefix = entry_prefix.get().strip()
    suffix = entry_suffix.get().strip()

    if not (prefix.isdigit() and suffix.isdigit()):
        messagebox.showwarning("输入错误", "请输入数字形式的前两位和后两位")
        return

    try:
        # 判断数据来源
        if source_var.get() == "online":
            stock_df = ak.stock_info_a_code_name()
        else:
            if not os.path.exists("A股股票列表.xlsx"):
                messagebox.showerror("文件不存在", "找不到文件 A股股票列表.xlsx，请确认已放在当前目录下。")
                return
            stock_df = pd.read_excel("A股股票列表.xlsx", dtype={"code": str})


        stock_df['code'] = stock_df['code'].astype(str)
        print(stock_df['code'])

        matched_df = stock_df[
            stock_df['code'].str.startswith(prefix) &
            stock_df['code'].str.endswith(suffix)
        ]

        output_text.delete(1.0, tk.END)
        if matched_df.empty:
            output_text.insert(tk.END, f"没有找到以 {prefix} 开头、{suffix} 结尾的股票代码。")
        else:
            for _, row in matched_df.iterrows():
                output_text.insert(tk.END, f"{row['code']} - {row['name']}\n")

    except Exception as e:
        messagebox.showerror("错误", f"查询出错：{e}")

# 创建主窗口
window = tk.Tk()
window.title("A股股票代码查询工具")
window.geometry("550x450")

# 数据来源选择
source_var = tk.StringVar(value="online")
frame_source = tk.Frame(window)
frame_source.pack(pady=10)

tk.Label(frame_source, text="请选择数据来源：").pack(side=tk.LEFT)
tk.Radiobutton(frame_source, text="线上查询（akshare）", variable=source_var, value="online").pack(side=tk.LEFT, padx=5)
tk.Radiobutton(frame_source, text="本地文件（A股股票列表.xlsx）", variable=source_var, value="local").pack(side=tk.LEFT, padx=5)

# 输入部分
frame_input = tk.Frame(window)
frame_input.pack(pady=10)

tk.Label(frame_input, text="股票代码前两位:").grid(row=0, column=0, padx=5)
entry_prefix = tk.Entry(frame_input, width=10)
entry_prefix.grid(row=0, column=1, padx=5)

tk.Label(frame_input, text="股票代码后两位:").grid(row=0, column=2, padx=5)
entry_suffix = tk.Entry(frame_input, width=10)
entry_suffix.grid(row=0, column=3, padx=5)

# 查询按钮
btn_query = tk.Button(window, text="查询", command=query_stock)
btn_query.pack(pady=10)

# 输出框
output_text = scrolledtext.ScrolledText(window, width=65, height=15)
output_text.pack(pady=10)

# 启动主循环
window.mainloop()
