"""LinkedIn figure: AgentDojo banking, attacks succeeded vs legitimate tasks completed."""
import glob
import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt

RUNS = sys.argv[1]  # .../llm_runs/<model>/important_instructions
OUT = sys.argv[2]
DRAFT = "--draft" in sys.argv

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e6e5e0"
BLUE, ORANGE = "#2a78d6", "#eb6834"  # validated pair (CVD ΔE 24.7, normal ΔE 33.6)
plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]

# Worst case (ground-truth replay, deterministic): (label, legit tasks %, attacks %)
WORST = [
    ("No protection", 16 / 16, 143 / 144),
    ("AgenticZeroTrust, no human", 11 / 16, 0 / 144),
    ("AgenticZeroTrust\n+ attentive human", 15 / 16, 0 / 144),
    ("AgenticZeroTrust\n+ human who approves everything", 15 / 16, 127 / 144),
]


def llm_rows():
    rows, complete = [], True
    for name, label in [("undefended", "No protection"), ("azt-known-nohuman", "AgenticZeroTrust, no human"),
                        ("azt-known-attentive", "AgenticZeroTrust\n+ attentive human")]:
        rs = [(os.path.basename(f), json.loads(Path(f).read_text())) for f in glob.glob(os.path.join(RUNS, name, "*.json"))]
        rs = [(f, r) for f, r in rs if r["error"] is None]
        clean = [r for f, r in rs if f.endswith("__none.json")]
        att = [r for f, r in rs if not f.endswith("__none.json")]
        complete &= len(clean) == 16 and len(att) == 144
        u = sum(r["utility"] for r in clean) / len(clean) if clean else 0
        a = sum(r["attack_success"] for r in att) / len(att) if att else 0
        rows.append((label, u, a))
    return rows, complete


def panel(ax, title, subtitle, rows):
    n = len(rows)
    h = 0.34
    for i, (label, util, asr) in enumerate(rows):
        y = n - 1 - i
        for dy, v, c in [(h / 2 + 0.02, asr, ORANGE), (-h / 2 - 0.02, util, BLUE)]:
            ax.barh(y + dy, max(v, 0.004), height=h, color=c, edgecolor=SURFACE, linewidth=2)
            ax.text(v + 0.015, y + dy, f"{v * 100:.0f}%", va="center", ha="left", fontsize=15,
                    color=INK, fontweight="bold" if c == ORANGE else "normal")
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1], fontsize=14, color=INK)
    ax.set_xlim(0, 1.12)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=12, color=MUTED)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0, pad=8)
    ax.set_title(title, loc="left", fontsize=18, fontweight="bold", color=INK, pad=30)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=13, color=INK2)


llm, complete = llm_rows()
fig = plt.figure(figsize=(12, 12), dpi=100, facecolor=SURFACE)
fig.text(0.04, 0.955, "Constrain what the agent can do, not what it thinks",
         fontsize=27, fontweight="bold", color=INK)
fig.text(0.04, 0.922, "AgentDojo banking benchmark (ETH Zurich): 16 user tasks × 9 prompt-injection attacks",
         fontsize=15, color=INK2)
# legend (two series, also direct-labelled by value)
for x, c, t in [(0.04, ORANGE, "Attacks that succeeded (lower is better)"),
                (0.46, BLUE, "Legitimate tasks completed, no attack (higher is better)")]:
    fig.patches.append(plt.Rectangle((x, 0.887), 0.018, 0.018, color=c, transform=fig.transFigure))
    fig.text(x + 0.026, 0.896, t, fontsize=13.5, color=INK, va="center")

ax1 = fig.add_axes([0.36, 0.50, 0.60, 0.31], facecolor=SURFACE)
panel(ax1, "Worst case: the agent obeys the attacker perfectly",
      "Model-independent: the attacker's tool calls are executed verbatim", WORST)
ax2 = fig.add_axes([0.36, 0.105, 0.60, 0.25], facecolor=SURFACE)
panel(ax2, "Real model: gpt-4o-mini" + ("" if complete else "  (DRAFT, partial run)"),
      "AgentDojo 'important_instructions' attack", llm)

fig.text(0.04, 0.035, "Human approval is simulated. 'No human' = only payees the user named or already paid are allowed.\n"
         "Open source, reproducible: github.com/HamdiM99/AgenticZeroTrust",
         fontsize=11.5, color=MUTED, linespacing=1.5)
fig.savefig(OUT, facecolor=SURFACE)
print("complete" if complete else "partial", llm)
