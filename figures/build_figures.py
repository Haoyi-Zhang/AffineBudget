"""Draw symbolic FCFS diagrams directly, without a TeX backend."""
from pathlib import Path
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

plt.rcParams.update({"font.family": "STIXGeneral", "font.size": 9.5,
                     "mathtext.fontset": "stix", "text.usetex": False,
                     "pdf.fonttype": 42, "ps.fonttype": 42})
META = {"Creator": "Matplotlib", "CreationDate": None, "ModDate": None}

def canvas(width, height, limits):
    fig, ax = plt.subplots(figsize=(width / 2.54, height / 2.54))
    ax.set(xlim=limits[:2], ylim=limits[2:])
    ax.axis("off")
    fig.subplots_adjust(left=.01, right=.99, bottom=.02, top=.98)
    return fig, ax

def box(ax, x, y, text, width=2.2, height=.85):
    ax.add_patch(Rectangle((x-width/2, y-height/2), width, height,
                           facecolor="white", edgecolor="black", linewidth=.8))
    ax.text(x, y, text, ha="center", va="center", linespacing=1.25)

def arrow(ax, start, end, dashed=False):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=9,
                                linewidth=.8, color="black",
                                linestyle="--" if dashed else "-"))

def running(out):
    fig, ax = canvas(14.5, 6.8, (-.2, 12.3, -2.6, 2.8))
    box(ax, 1.2, 0, "Prefix\n"+r"$H+K\phi$", 2.3)
    for y, label in [(1.65, "Preparation "+r"$A$"+"\n"+r"$L$"),
                     (0, "Preparation "+r"$B_+$"+"\n"+r"$L+\delta+\theta$"),
                     (-1.65, "Preparation "+r"$B_-$"+"\n"+r"$L+\delta-\theta$")]:
        box(ax, 5.3, y, label, 2.8)
        arrow(ax, (2.35, 0), (3.9, y))
    ax.add_patch(Rectangle((8.45, -2.2), 3.5, 4.4,
                           facecolor="none", edgecolor=".45", linewidth=.7))
    ax.text(10.2, 2.45, "Shared bank", ha="center", va="center")
    box(ax, 10.2, 1.25, "Request "+r"$A$"+"\nservice 1", 2.6)
    box(ax, 10.2, -1.25, "Request "+r"$B$"+"\nservice 1", 2.6)
    arrow(ax, (6.7, 1.65), (8.9, 1.25))
    arrow(ax, (6.7, 0), (8.9, -1.25))
    arrow(ax, (6.7, -1.65), (8.9, -1.25))
    arrow(ax, (10.2, .825), (10.2, -.825), dashed=True)
    ax.text(10.4, 0, r"$A\prec B$", va="center", ha="left")
    fig.savefig(out/"running-example.pdf", metadata=META)
    plt.close(fig)

def order_change(out):
    fig, ax = canvas(14.5, 7.0, (-.05, 12.2, -3.7, 1.1))
    def bar(x, y, w, label, gray=False):
        ax.add_patch(Rectangle((x, y-.23), w, .46, edgecolor="black",
                               facecolor=".9" if gray else "white", linewidth=.8))
        ax.text(x+w/2, y, label, ha="center", va="center")
    for offset, name in [(0, "Nominal"), (-2.1, "Perturbed")]:
        ax.text(1.55, offset+.66, name, ha="right", va="center")
        ax.text(1.55, offset, "Bank", ha="right", va="center")
        ax.text(1.55, offset-.65, "Tail", ha="right", va="center")
    bar(1.8, 0, 4.1, r"$A:\ M$")
    bar(5.9, 0, .85, r"$B$", True)
    bar(6.75, -.65, 4.1, r"$T:\ M$")
    ax.text(1.8, .36, r"$1$", ha="center")
    ax.text(6.75, .36, r"$M+2$", ha="center")
    ax.text(10.85, -1.15, r"$C_0=2M+2$", ha="right")
    bar(1.8, -2.1, .85, r"$B$", True)
    bar(2.65, -2.1, 4.1, r"$A:\ M$")
    bar(2.65, -2.75, 4.1, r"$T:\ M$")
    ax.plot([2.65, 2.65], [-2.4, -3.12], color=".35", ls="--", lw=.7)
    ax.text(2.65, -3.25, r"$2-\varepsilon$", ha="center", va="top")
    ax.text(1.8, -1.72, r"$1-\varepsilon$", ha="center")
    ax.text(7.1, -2.45, r"$C=M+2-\varepsilon$"+"\n"+r"$\Delta C=M+\varepsilon$",
            ha="left", va="center", linespacing=1.45)
    fig.savefig(out/"order-change.pdf", metadata=META)
    plt.close(fig)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    running(args.outdir)
    order_change(args.outdir)
