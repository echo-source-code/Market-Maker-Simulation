"""
Opens two figure windows:
  1. the baseline: skew vs no skew
  2. the three extensions (adverse selection, sweeps, Avellaneda-Stoikov)
 
Uses N paths per point. Raise N for smoother plots (slower).
Set SAVE = True to also write results.png and extensions.png (for the README).
"""
import numpy as np
import matplotlib.pyplot as plt
from market_maker import simulate, run_many, theory_mean_pnl
 
N = 500
HALF_SPREAD = 1.0
SAVE = True
 
# ---------------------------------------------------------------------------
# Figure 1: baseline
# ---------------------------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
 
# Left: distribution of final PnL, no skew vs skew
for skew, colour in [(0.0, "tab:red"), (0.05, "tab:blue")]:
    pnls, _ = run_many(skew, HALF_SPREAD, n_paths=N)
    ax1.hist(pnls, bins=40, alpha=0.6, color=colour, label=f"skew = {skew}")
ax1.set_xlabel("Final PnL")
ax1.set_ylabel("Number of simulated paths")
ax1.set_title("Skewing narrows the PnL distribution")
ax1.legend()
 
# Right: one inventory path each, same random seed
for skew, colour in [(0.0, "tab:red"), (0.05, "tab:blue")]:
    _, inv = simulate(skew, HALF_SPREAD, rng=np.random.default_rng(1))
    ax2.plot(inv, color=colour, label=f"skew = {skew}")
ax2.set_xlabel("Time step")
ax2.set_ylabel("Inventory")
ax2.set_title("Inventory over one simulated day")
ax2.legend()
 
plt.tight_layout()
if SAVE:
    plt.savefig("results.png", dpi=150)
 
# ---------------------------------------------------------------------------
# Figure 2: extensions
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(11, 8))
ax1, ax2, ax3, ax4 = axes.flatten()
 
# Extension 1: adverse selection. Mean PnL against impact, bars are +/- 1 std
impacts = [0.0, 0.1, 0.3, 0.5]
for skew, colour in [(0.0, "tab:red"), (0.05, "tab:blue")]:
    means, stds = [], []
    for impact in impacts:
        pnls, _ = run_many(skew, HALF_SPREAD, n_paths=N, impact=impact)
        means.append(pnls.mean())
        stds.append(pnls.std())
    ax1.errorbar(impacts, means, yerr=stds, marker="o", capsize=4,
                 color=colour, label=f"skew = {skew}")
ax1.set_xlabel("Impact (price move against us after a fill)")
ax1.set_ylabel("PnL (mean, bars = +/- 1 std)")
ax1.set_title("1. Adverse selection hurts most without skew")
ax1.legend()
 
# Extension 2a: sweep the half-spread, simulated points against theory curve
spreads = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
sim = [run_many(0.0, hs, n_paths=N)[0].mean() for hs in spreads]
grid = np.linspace(0.1, 3.0, 200)
ax2.plot(grid, theory_mean_pnl(grid), color="black", label="theory")
ax2.scatter(spreads, sim, color="tab:orange", zorder=3, label="simulated")
ax2.set_xlabel("Half-spread")
ax2.set_ylabel("Mean PnL (no skew)")
ax2.set_title("2a. Mean PnL peaks at an intermediate spread")
ax2.legend()
 
# Extension 2b: sweep k, simulated points against theory curve
ks = [1.0, 1.5, 2.0, 3.0]
sim_k = [run_many(0.0, HALF_SPREAD, n_paths=N, k=k)[0].mean() for k in ks]
kgrid = np.linspace(0.8, 3.2, 200)
ax3.plot(kgrid, theory_mean_pnl(HALF_SPREAD, k=kgrid), color="black", label="theory")
ax3.scatter(ks, sim_k, color="tab:orange", zorder=3, label="simulated")
ax3.set_xlabel("k (how fast fill rate falls with distance)")
ax3.set_ylabel("Mean PnL (no skew)")
ax3.set_title("2b. Simulation matches theory across k")
ax3.legend()
 
# Extension 3: risk and return. Each point is one strategy
skews = [0.0, 0.01, 0.02, 0.05, 0.10]
fixed = [run_many(s, HALF_SPREAD, n_paths=N)[0] for s in skews]
ax4.plot([p.std() for p in fixed], [p.mean() for p in fixed],
         marker="o", color="tab:blue", label="fixed skew")
for s, p in zip(skews, fixed):
    ax4.annotate(f"{s}", (p.std(), p.mean()), textcoords="offset points",
                 xytext=(5, -12), fontsize=8, color="tab:blue")
 
gammas = [0.005, 0.01, 0.02, 0.05]
avs = [run_many(0.0, HALF_SPREAD, n_paths=N, avellaneda=True, gamma=g)[0]
       for g in gammas]
ax4.plot([p.std() for p in avs], [p.mean() for p in avs],
         marker="s", color="tab:green", label="Avellaneda-Stoikov")
for g, p in zip(gammas, avs):
    ax4.annotate(f"{g}", (p.std(), p.mean()), textcoords="offset points",
                 xytext=(5, 5), fontsize=8, color="tab:green")
ax4.set_xlabel("Std of PnL (risk)")
ax4.set_ylabel("Mean PnL (return)")
ax4.set_title("3. Avellaneda-Stoikov vs fixed skew (up and left is better)")
ax4.margins(x=0.08, y=0.08)       # leave room so point labels are not clipped
ax4.legend()
 
plt.tight_layout()
if SAVE:
    plt.savefig("extensions.png", dpi=150)
 
plt.show()      # opens both figures; close the windows to end the script