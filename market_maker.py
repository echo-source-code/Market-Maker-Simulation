"""
A toy market maker.
 
Question: a market maker earns the bid-ask spread, but every fill changes its
inventory, and inventory is exposed to price moves. Does leaning your quotes
against your inventory ("skewing") reduce that risk, and what does it cost?
 
Model (deliberately simple):
  * The fair price (mid) is a random walk.
  * We quote a bid and an ask around mid.
  * Orders hit a quote as a Poisson process whose rate falls as the quote
    moves away from mid:   rate = A * exp(-k * distance)
  * Hit on our ask -> we sell one unit (inventory -1). Hit on our bid -> we buy (+1).
  * Skew: shift both quotes down when we are long (so we sell more, buy less),
    and up when we are short.
 
Extensions (all off by default, so the original results are unchanged):
  1. impact       Adverse selection: the price moves against us after each fill.
  2. (sweeps)     Vary the spread and k in the experiments at the bottom.
  3. avellaneda   Use the Avellaneda-Stoikov closed-form quotes instead of a
                  fixed skew and spread.
"""
import numpy as np
 
 
def simulate(skew, half_spread, n_steps=2000, sigma=0.1, A=1.0, k=1.5, rng=None,
             impact=0.0, avellaneda=False, gamma=0.01):
    """Run one path. Returns final PnL and the inventory path.
 
    impact      : price moves by this much against us after each fill
    avellaneda  : if True, ignore skew and half_spread and use the
                  Avellaneda-Stoikov quotes with risk aversion gamma
    """
    rng = rng or np.random.default_rng()
 
    mid = 100.0
    cash = 0.0
    inventory = 0
    inventory_path = np.empty(n_steps)
 
    for t in range(n_steps):
        # 1. Quotes
        if avellaneda:
            time_left = n_steps - t
            shift = gamma * sigma**2 * time_left * inventory
            half = 0.5 * (gamma * sigma**2 * time_left
                          + (2 / gamma) * np.log(1 + gamma / k))
        else:
            shift = skew * inventory
            half = half_spread
        bid = mid - half - shift
        ask = mid + half - shift
 
        # 2. How far is each quote from mid? (closer -> more likely to be hit)
        bid_distance = mid - bid
        ask_distance = ask - mid
 
        # 3. Probability of at least one hit in this step (Poisson, dt = 1)
        p_bid_hit = 1 - np.exp(-A * np.exp(-k * bid_distance))
        p_ask_hit = 1 - np.exp(-A * np.exp(-k * ask_distance))
 
        # 4. Fills (after a fill the price moves against us by `impact`)
        if rng.random() < p_bid_hit:   # someone sells to us at our bid
            cash -= bid
            inventory += 1
            mid -= impact              # a seller often knows the price is falling
        if rng.random() < p_ask_hit:   # someone buys from us at our ask
            cash += ask
            inventory -= 1
            mid += impact              # a buyer often knows the price is rising
 
        # 5. Price moves
        mid += sigma * rng.standard_normal()
 
        inventory_path[t] = inventory
 
    pnl = cash + inventory * mid      # mark remaining inventory to market
    return pnl, inventory_path
 
 
def run_many(skew, half_spread, n_paths=2000, seed=0, **kwargs):
    rng = np.random.default_rng(seed)
    pnls = np.empty(n_paths)
    max_abs_inventory = np.empty(n_paths)
    for i in range(n_paths):
        pnl, inv = simulate(skew, half_spread, rng=rng, **kwargs)
        pnls[i] = pnl
        max_abs_inventory[i] = np.abs(inv).max()
    return pnls, max_abs_inventory
 
 
def theory_mean_pnl(half_spread, n_steps=2000, A=1.0, k=1.5):
    """Expected PnL with no skew and no impact: each step, each side is hit
    with probability p and earns half_spread per fill."""
    p = 1 - np.exp(-A * np.exp(-k * half_spread))
    return n_steps * 2 * half_spread * p
 
 
def row(label, pnls, max_inv):
    print(f"{label:>10} {pnls.mean():>10.1f} {pnls.std():>9.1f} "
          f"{pnls.mean() / pnls.std():>9.2f} {max_inv.mean():>14.1f}")
 
 
HEADER = f"{'':>10} {'mean PnL':>10} {'std PnL':>9} {'mean/std':>9} {'avg max |inv|':>14}"
 
if __name__ == "__main__":
    N = 1000          # paths per row; raise for smoother numbers (slower)
 
    print("BASELINE: effect of skew (half_spread = 1.0)")
    print(HEADER.replace("          ", "      skew", 1))
    for skew in [0.0, 0.01, 0.02, 0.05, 0.10]:
        row(f"{skew:.2f}", *run_many(skew, 1.0, n_paths=N))
 
    print("\nAdverse selection (half_spread = 1.0)")
    print(HEADER.replace("          ", "    impact", 1))
    for skew in [0.0, 0.05]:
        print(f"  skew = {skew}")
        for impact in [0.0, 0.1, 0.3, 0.5]:
            row(f"{impact:.1f}", *run_many(skew, 1.0, n_paths=N, impact=impact))
 
    print("\nSweep the half-spread (skew = 0)")
    print(f"{'half_spread':>12} {'simulated':>10} {'theory':>9}")
    for hs in [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        pnls, _ = run_many(0.0, hs, n_paths=N)
        print(f"{hs:>12.2f} {pnls.mean():>10.1f} {theory_mean_pnl(hs):>9.1f}")
 
    print("\nSweep k (skew = 0, half_spread = 1.0)")
    print(f"{'k':>12} {'simulated':>10} {'theory':>9}")
    for k in [1.0, 1.5, 2.0, 3.0]:
        pnls, _ = run_many(0.0, 1.0, n_paths=N, k=k)
        print(f"{k:>12.1f} {pnls.mean():>10.1f} {theory_mean_pnl(1.0, k=k):>9.1f}")
 
    print("\nAvellaneda-Stoikov vs fixed skew")
    print(HEADER.replace("          ", "  strategy", 1))
    row("skew 0.05", *run_many(0.05, 1.0, n_paths=N))
    for gamma in [0.005, 0.01, 0.02, 0.05]:
        row(f"AS g={gamma}", *run_many(0.0, 1.0, n_paths=N, avellaneda=True, gamma=gamma))