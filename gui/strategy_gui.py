# adaptive_dca_ai/gui/strategy_gui.py
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import tkinter as tk
from tkinter import messagebox
from adaptive_dca_ai.tools.compare_candidates import compare_top_k
import os

def run_comparison():
    try:
        results, best = compare_top_k(k=5)
        if not results:
            messagebox.showwarning("結果", "沒有可用策略")
            return

        summary = "\n".join([
            f"{'⭐' if r is best else '  '} ID={r['id']} | {r['strategy']} | PnL={r['pnl']:.2f} | Sharpe={r['sharpe']:.2f}"
            for r in results
        ])
        messagebox.showinfo("策略比較完成", f"最佳策略已儲存為 JSON\n\n{summary}")
    except Exception as e:
        messagebox.showerror("錯誤", f"執行失敗：{e}")

def open_outputs_folder():
    outdir = os.path.join(pathlib.Path(__file__).parent.parent, "tools", "outputs")
    os.makedirs(outdir, exist_ok=True)
    os.startfile(outdir)

root = tk.Tk()
root.title("策略比較工具")
root.geometry("400x200")

label = tk.Label(root, text="📊 策略模擬與比較", font=("Arial", 16))
label.pack(pady=10)

btn_run = tk.Button(root, text="執行比較", font=("Arial", 12), command=run_comparison)
btn_run.pack(pady=5)

btn_open = tk.Button(root, text="開啟報表資料夾", font=("Arial", 12), command=open_outputs_folder)
btn_open.pack(pady=5)

root.mainloop()