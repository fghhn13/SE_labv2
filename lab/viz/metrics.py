from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
import matplotlib.pyplot as plt


def load_episode_csv(path: str | Path) -> pd.DataFrame:
    """
    从 CsvEpisodeLogger 生成的 CSV 中读入训练结果。
    期望列：episode, success, cost, steps
    """
    path = Path(path)
    df = pd.read_csv(path)
    # 确保列存在
    required = {"episode", "success", "cost", "steps"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV {path}: {missing}")
    # 为了支持“多次运行追加到同一个 CSV”的情况：
    # - 原始 CsvEpisodeLogger 的 episode 列会在每次运行从 0 重新开始
    # - 这里引入一个全局连续索引 global_episode，作为绘图的 x 轴
    df = df.reset_index(drop=True)
    df["global_episode"] = df.index
    return df


def _rolling_mean(series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=1).mean()


def plot_success_rate(
    df: pd.DataFrame,
    window: int = 10,
    out_path: Optional[str | Path] = None,
) -> None:
    """
    绘制滑动平均成功率曲线。
    """
    episodes = df["global_episode"]
    success = df["success"].astype(float)
    success_rate = _rolling_mean(success, window=window)

    plt.figure(figsize=(6, 4))
    plt.plot(episodes, success_rate, label=f"success_rate (window={window})")
    plt.ylim(-0.05, 1.05)
    plt.xlabel("episode")
    plt.ylabel("success rate")
    plt.title("Episode success rate (rolling mean)")
    plt.grid(True, alpha=0.3)
    plt.legend()

    if out_path is None:
        plt.show()
    else:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(out_path)
        plt.close()


def plot_steps_and_cost(
    df: pd.DataFrame,
    window: int = 10,
    out_path: Optional[str | Path] = None,
) -> None:
    """
    绘制步数与 cost 的滑动平均曲线（双子图）。
    """
    episodes = df["global_episode"]
    steps_rm = _rolling_mean(df["steps"], window=window)
    cost_rm = _rolling_mean(df["cost"], window=window)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 6), sharex=True)

    ax1.plot(episodes, steps_rm, label=f"steps (window={window})", color="tab:blue")
    ax1.set_ylabel("steps")
    ax1.set_title("Episode steps (rolling mean)")
    ax1.grid(True, alpha=0.3)

    ax2.plot(episodes, cost_rm, label=f"cost (window={window})", color="tab:orange")
    ax2.set_xlabel("episode")
    ax2.set_ylabel("cost")
    ax2.set_title("Episode cost (rolling mean)")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()

    if out_path is None:
        plt.show()
    else:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path)
        plt.close(fig)


def plot_all_metrics(
    csv_path: str | Path,
    output_dir: Optional[str | Path] = None,
    window: int = 10,
) -> None:
    """
    读取 CSV 并一次性生成基础指标图：
    - success_rate.png
    - steps_cost.png
    如果 output_dir 为 None，则直接使用 plt.show() 弹出窗口。
    """
    df = load_episode_csv(csv_path)

    if output_dir is None:
        # 交互式：只 show，不写文件
        plot_success_rate(df, window=window, out_path=None)
        plot_steps_and_cost(df, window=window, out_path=None)
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        plot_success_rate(df, window=window, out_path=output_dir / "success_rate.png")
        plot_steps_and_cost(df, window=window, out_path=output_dir / "steps_cost.png")

