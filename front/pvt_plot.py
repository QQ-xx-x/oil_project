"""
PVT 气水截面曲线绘图组件。
"""
from __future__ import annotations

import numpy as np
from matplotlib import rcParams
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QWidget, QVBoxLayout


rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
rcParams["axes.unicode_minus"] = False


def _clamp01(values):
    return np.clip(values, 0.0, 1.0)


def compute_gas_water_section(sw, sg, swi, sor, sgc, num_points=200):
    """根据当前初始工况和 Corey 模型生成气水截面曲线。"""
    so_fixed = 1.0 - sw - sg
    if so_fixed < 0.0 or so_fixed > 1.0:
        raise ValueError(f"So_fixed={so_fixed:.4f} 超出 [0, 1]，请检查 Sw 和 Sg。")

    sw_max = 1.0 - sgc - so_fixed
    if sw_max <= swi:
        raise ValueError(
            "无有效绘图区间：需要满足 Swi < 1 - Sgc - So_fixed。"
        )

    sw_denom = 1.0 - swi - sor
    sg_denom = 1.0 - sgc - swi - sor
    if sw_denom <= 0.0:
        raise ValueError("无效参数：1 - Swi - Sor 必须大于 0。")
    if sg_denom <= 0.0:
        raise ValueError("无效参数：1 - Sgc - Swi - Sor 必须大于 0。")

    sw_values = np.linspace(swi, sw_max, num_points)
    sg_values = 1.0 - sw_values - so_fixed

    sw_norm = _clamp01((sw_values - swi) / sw_denom)
    sg_norm = _clamp01((sg_values - sgc) / sg_denom)

    krw = sw_norm * sw_norm
    krg = sg_norm * sg_norm

    return {
        "so_fixed": so_fixed,
        "sw_values": sw_values,
        "sg_values": sg_values,
        "krw": krw,
        "krg": krg,
    }


class PVTPlotWidget(QWidget):
    """显示 PVT 气水截面曲线的 Matplotlib 组件。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(facecolor="white")
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def plot_gas_water_section(self, sw, sg, swi, sor, sgc):
        curves = compute_gas_water_section(sw, sg, swi, sor, sgc)
        so_fixed = curves["so_fixed"]

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor("white")

        sw_values = curves["sw_values"]
        krg = curves["krg"]
        krw = curves["krw"]

        marker_step = max(1, len(sw_values) // 24)
        ax.plot(
            sw_values,
            krg,
            color="#3f68b1",
            linewidth=2.6,
            marker="o",
            markersize=5.5,
            markevery=marker_step,
            label=r"$k_{rg}$ 气的相对渗透率",
        )
        ax.plot(
            sw_values,
            krw,
            color="#d56a33",
            linewidth=2.6,
            marker="s",
            markersize=5.5,
            markevery=marker_step,
            label=r"$k_{rw}$ 水的相对渗透率",
        )

        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel(r"含水饱和度 $S_w$", fontsize=18)
        ax.set_ylabel(r"相对渗透率 $k_r$", fontsize=18)
        ax.set_title(
            f"与当前初始工况对应的气水截面曲线（So_fixed={so_fixed:.4f}）",
            fontsize=18,
            pad=12,
        )
        ax.grid(True, linestyle="--", linewidth=1.0, alpha=0.5)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0.96), frameon=False, fontsize=12)
        ax.tick_params(axis="both", labelsize=13)

        for spine in ax.spines.values():
            spine.set_linewidth(1.1)

        self.figure.tight_layout()
        self.canvas.draw()
        return so_fixed
