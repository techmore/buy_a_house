#!/usr/bin/env python3
"""
FHA first-time-buyer model — Bucks & Montgomery County, PA (Sept 2026).

Two ways to deploy $6,500/yr of surplus cash, compared fairly:
  A) Prepay the FHA mortgage until it is retired, then invest the freed-up
     payment at the same rate as the Roth (so both paths deploy identical
     dollars over the 30-year window).
  B) Contribute $6,500/yr to a Roth IRA every year for 30 years.

All figures are deterministic projections, not guarantees.
"""
import json
from collections import OrderedDict

# ----------------------------------------------------------------------------
# VERIFIED INPUTS (retrieved Sept 10, 2026)
# ----------------------------------------------------------------------------
RATE_FHA = 0.06162          # avg 30-yr FHA, Fortune/Mortgage Research Center 9/10/2026
RATE_CONV = 0.06810         # avg 30-yr conventional, same source
UFMIP = 0.0175              # FHA upfront MIP
ANNUAL_MIP = 0.0055         # annual MIP, <5% down, base loan <= conforming limit
MIP_MONTHS_STD = 360        # <10% down -> life of loan
MIP_MONTHS_10PCT = 132      # >=10% down -> 11 years

FHA_LIMIT = 630_200         # HUD cy2026-forward-limits.txt: Bucks & Montgomery 1-unit
TERM = 30                   # years
TERM_MONTHS = TERM * 12     # 360 payment periods

# Effective property tax rates (Census ACS 2019-2023, via propertytaxbyzip.com)
TAX_RATE = {"Upper Black Eddy 18972": 0.0098,
            "Harleysville 19438": 0.0136,
            "Collegeville 19426": 0.0145}

# Estimates, not verified facts
INSURANCE = 1_500           # annual homeowners premium, ~$300-400k home, PA
ROTH_RETURN = 0.07          # long-run nominal market assumption
ROTH_CAP = 7_500            # IRA annual ceiling (verify current year)

PRICES = [250_000, 300_000, 350_000, 400_000, 450_000]


def pmt(principal, annual_rate, months):
    """Level monthly payment covering principal + interest."""
    if principal <= 0:
        return 0.0
    r = annual_rate / 12.0
    if r == 0:
        return principal / months
    return principal * r / (1 - (1 + r) ** -months)


def balance_after(balance, annual_rate, months, extra_monthly=0.0):
    """Remaining balance after `months` payments, with optional extra monthly."""
    r = annual_rate / 12.0
    base = pmt(balance, annual_rate, TERM_MONTHS)
    for _ in range(months):
        if balance <= 0:
            return 0.0
        interest = balance * r
        principal = min(base - interest, balance)
        balance -= principal
        if extra_monthly:
            balance -= min(extra_monthly, balance)
        balance = max(balance, 0.0)
    return balance


def amortize(balance, annual_rate, extra_monthly=0.0, extra_annual=0.0,
             extra_annual_month=1):
    """Amortize to payoff under a fixed extra-payment plan."""
    r = annual_rate / 12.0
    base = pmt(balance, annual_rate, TERM_MONTHS)
    rows = []
    total_interest = 0.0
    m = 0
    while balance > 0 and m < TERM_MONTHS * 3:
        m += 1
        interest = balance * r
        principal = min(base - interest, balance)
        if principal < 0:
            principal = 0.0
        pay = interest + principal
        balance -= principal
        if extra_monthly:
            add = min(extra_monthly, balance)
            balance -= add
            principal += add
            pay += add
        if extra_annual and extra_annual_month and m % 12 == extra_annual_month % 12:
            add = min(extra_annual, balance)
            balance -= add
            principal += add
            pay += add
        total_interest += interest
        rows.append((m, pay, principal, interest, max(balance, 0.0)))
    return {"base_payment": base, "rows": rows, "months_m": len(rows),
            "months": len(rows), "total_interest": total_interest,
            "schedule": rows}


def fha_monthly(price, down_pct, tax_rate, rate=RATE_FHA,
                finance_ufmip=True, insurance=INSURANCE, hoa=0.0):
    """Full FHA monthly housing cost breakdown."""
    down = price * down_pct
    base_loan = price - down
    ufmip_amt = base_loan * UFMIP
    total_loan = base_loan + (ufmip_amt if finance_ufmip else 0.0)
    mip_months = MIP_MONTHS_10PCT if down_pct >= 0.10 else MIP_MONTHS_STD
    mip_monthly = base_loan * ANNUAL_MIP / 12.0
    pi = pmt(total_loan, rate, TERM_MONTHS)
    tax_monthly = price * tax_rate / 12.0
    ins_monthly = insurance / 12.0
    total = pi + mip_monthly + tax_monthly + ins_monthly + hoa
    return {
        "price": price, "down": down, "base_loan": base_loan,
        "ufmip": ufmip_amt, "total_loan": total_loan,
        "pi": pi, "mip_monthly": mip_monthly, "mip_months": mip_months,
        "tax_monthly": tax_monthly, "ins_monthly": ins_monthly, "hoa": hoa,
        "total_monthly": total, "piti_no_mip": pi + tax_monthly + ins_monthly + hoa,
    }


def closing_costs(price, tax_rate, loan_amount, financed_ufmip=True):
    """Itemized buyer closing costs, typical for PA."""
    transfer = price * 0.01
    title = max(1_200, price * 0.005)
    items = OrderedDict([
        ("Origination / lender fees", loan_amount * 0.005),
        ("Underwriting", 1_195),
        ("Appraisal", 700),
        ("Credit report", 75),
        ("Title search + lender's title insurance", title),
        ("PA realty transfer tax + recording", transfer + 250),
        ("Tax service / settlement fees", 95),
        ("Prepaid property tax escrow (~3 mo)", price * tax_rate * (90 / 365)),
        ("Prepaid homeowners insurance", INSURANCE * 1.25),
    ])
    if not financed_ufmip:
        items["Upfront MIP paid in cash"] = loan_amount * UFMIP
    return items


def fv_contributions(annual_contribution, years, rate=ROTH_RETURN):
    """Future value of contributions made at the START of each year."""
    bal = 0.0
    for _ in range(years):
        bal = (bal + annual_contribution) * (1 + rate)
    return bal


def fv_contributions_monthly(monthly, months, rate=ROTH_RETURN):
    """Future value of monthly contributions at month-end."""
    r = rate / 12.0
    bal = 0.0
    for _ in range(months):
        bal = (bal + monthly) * (1 + r)
    return bal


def build_paths(price, extra_annual=6_500, rate=RATE_FHA,
                down_pct=0.035, years=TERM, reinvest=True,
                return_rate=ROTH_RETURN):
    """
    Path A: prepay the mortgage, then (optionally) invest the freed-up cash flow.
    Path B: Roth IRA contributions for the full horizon.
    When reinvest=True both paths deploy the same total dollars.
    """
    down = price * down_pct
    base_loan = price - down
    total_loan = base_loan * (1 + UFMIP)

    sched = amortize(total_loan, rate, extra_annual=extra_annual,
                     extra_annual_month=1)
    payoff_m = sched["months"]
    base = sched["base_payment"]

    # Balance at horizon under the prepayment plan
    b = total_loan
    r = rate / 12.0
    for m in range(1, years * 12 + 1):
        if b <= 0:
            b = 0.0
            break
        interest = b * r
        principal = min(base - interest, b)
        b -= principal
        if m % 12 == 1 % 12:
            b -= min(extra_annual, b)
        b = max(b, 0.0)
    balance_at_horizon = b

    # Cash flow freed up after the loan is retired, reinvested like the Roth
    freed = 0.0
    if payoff_m < years * 12 and reinvest:
        months_freed = years * 12 - payoff_m
        freed = fv_contributions_monthly(base, months_freed, return_rate)
        full_years_after = int(months_freed // 12)
        for k in range(full_years_after):
            remaining_years = (months_freed / 12.0) - k
            freed += extra_annual * (1 + return_rate) ** remaining_years

    roth = fv_contributions(extra_annual, years, return_rate)
    roth_monthly = fv_contributions_monthly(extra_annual / 12.0, years * 12,
                                            return_rate)

    baseline_balance = balance_after(total_loan, rate, years * 12)
    equity_adv = baseline_balance - balance_at_horizon

    path_a_total = equity_adv + freed

    return {
        "loan": {"down": down, "base_loan": base_loan, "total_loan": total_loan},
        "base_payment": base,
        "payoff_months": payoff_m,
        "payoff_years": payoff_m / 12.0,
        "total_interest_extra": sched["total_interest"],
        "balance_at_horizon": balance_at_horizon,
        "baseline_balance": baseline_balance,
        "equity_advantage": equity_adv,
        "freed_reinvested": freed,
        "path_a_wealth": path_a_total,
        "path_b_wealth": roth,
        "advantage_b_over_a": roth - path_a_total,
        "roth": roth,
        "roth_monthly": roth_monthly,
        "interest_saved_total": (
            amortize(total_loan, rate)["total_interest"] - sched["total_interest"]
        ),
    }


def analyze(price, tax_rate, extra=6_500, years=30, return_rate=ROTH_RETURN):
    m = fha_monthly(price, 0.035, tax_rate)
    return {"monthly": m, "paths": build_paths(price, extra, years=years,
                                               return_rate=return_rate)}


def money(x, cents=False):
    return f"${x:,.2f}" if cents else f"${x:,.0f}"


# ----------------------------------------------------------------------------
# RUN
# ----------------------------------------------------------------------------
out = OrderedDict()
out["rates"] = {"fha": RATE_FHA, "conventional": RATE_CONV,
                "roth_return": ROTH_RETURN, "ufmip": UFMIP,
                "annual_mip": ANNUAL_MIP, "fha_limit": FHA_LIMIT}

table = []
for price in PRICES:
    for loc, tr in TAX_RATE.items():
        m = fha_monthly(price, 0.035, tr)
        cc = sum(closing_costs(price, tr, m["base_loan"]).values())
        table.append({
            "price": price, "location": loc, "down_3_5": m["down"],
            "base_loan": m["base_loan"], "total_loan": m["total_loan"],
            "ufmip": m["ufmip"], "pi": m["pi"], "mip": m["mip_monthly"],
            "tax": m["tax_monthly"], "ins": m["ins_monthly"],
            "total_monthly": m["total_monthly"], "piti": m["piti_no_mip"],
            "closing_costs": cc, "cash_to_close": m["down"] + cc,
        })
out["purchase_power"] = table

table10 = []
for price in [300_000, 350_000, 400_000]:
    for loc, tr in TAX_RATE.items():
        m = fha_monthly(price, 0.10, tr)
        table10.append({
            "price": price, "location": loc, "down": m["down"],
            "base_loan": m["base_loan"], "pi": m["pi"], "mip": m["mip_monthly"],
            "tax": m["tax_monthly"], "total_monthly": m["total_monthly"],
            "mip_lifetime": m["mip_monthly"] * MIP_MONTHS_10PCT,
            "mip_std_lifetime": m["mip_monthly"] * MIP_MONTHS_STD,
        })
out["ten_percent_down"] = table10

head = analyze(350_000, TAX_RATE["Harleysville 19438"])
out["headline"] = head

sens = []
for rr in [0.04, 0.05, 0.06, 0.07, 0.08, 0.09]:
    p = build_paths(350_000, 6_500, return_rate=rr)
    sens.append({"return": rr, "path_a": p["path_a_wealth"],
                 "path_b": p["path_b_wealth"],
                 "advantage_b": p["advantage_b_over_a"]})
out["roth_sensitivity"] = sens

hor = []
for y in [5, 10, 15, 20, 25, 30]:
    p = build_paths(350_000, 6_500, years=y)
    hor.append({"year": y, "payoff_years": p["payoff_years"],
                "path_a": p["path_a_wealth"], "path_b": p["path_b_wealth"],
                "advantage_b": p["advantage_b_over_a"]})
out["horizon_sweep"] = hor

simple = {}
for price in [250_000, 350_000, 450_000]:
    p = build_paths(price, 6_500, reinvest=False)
    simple[price] = {"equity_advantage": p["equity_advantage"],
                     "roth": p["roth"], "payoff_years": p["payoff_years"]}
out["no_reinvest"] = simple

alt = {"prepay_monthly_542": {}, "buy_down_rate": {}}
price = 350_000
sched = amortize(price * 0.965 * (1 + UFMIP), RATE_FHA, extra_monthly=6_500 / 12)
alt["prepay_monthly_542"] = {"payoff_years": sched["months"] / 12.0,
                             "total_interest": sched["total_interest"]}
buydown_cost = price * 0.965 * 0.03
buydown_rate = RATE_FHA - 0.0075
m_buy = fha_monthly(price, 0.035, TAX_RATE["Harleysville 19438"], rate=buydown_rate)
m_norm = fha_monthly(price, 0.035, TAX_RATE["Harleysville 19438"])
alt["buy_down_rate"] = {
    "cost": buydown_cost, "new_rate": buydown_rate,
    "monthly_saving": m_norm["total_monthly"] - m_buy["total_monthly"],
    "breakeven_months": (buydown_cost / (m_norm["pi"] - m_buy["pi"])
                         if m_buy["pi"] != m_norm["pi"] else 0),
}
out["alternatives"] = alt

with open("model_output.json", "w") as f:
    json.dump(out, f, indent=2, default=str)

# ---------------- console report ----------------
print("=" * 96)
print("A. FHA PURCHASE POWER — 3.5% down, 6.162%, upfront MIP financed")
print("=" * 96)
print(f"{'Price':>9} {'Area':<24} {'Loan':>10} {'P&I':>8} {'MIP':>6} "
      f"{'Tax':>6} {'Ins':>5} {'All-in/mo':>10} {'Cash to close':>14}")
print("-" * 96)
for row in table:
    print(f"{money(row['price']):>9} {row['location']:<24} "
          f"{money(row['total_loan']):>10} {money(row['pi']):>8} "
          f"{money(row['mip']):>6} {money(row['tax']):>6} "
          f"{money(row['ins']):>5} {money(row['total_monthly']):>10} "
          f"{money(row['cash_to_close']):>14}")

print()
print("=" * 96)
print("B. $6,500/YR: PREPAY MORTGAGE vs ROTH IRA  ($350,000 Harleysville 19438)")
print("=" * 96)
p = head["paths"]
print(f"  Monthly P&I                      {money(p['base_payment'], True)}")
print(f"  All-in monthly (P&I+MIP+tax+ins) {money(head['monthly']['total_monthly'], True)}")
print(f"  Payoff with extra prepayment     {p['payoff_years']:.1f} years (vs 30.0)")
print(f"  Interest saved by prepaying      {money(p['interest_saved_total'])}")
print(f"  Balance owed yr 30 (prepay)      {money(p['balance_at_horizon'])}")
print(f"  Balance owed yr 30 (no extra)    {money(p['baseline_balance'])}")
print(f"  Equity advantage from prepaying  {money(p['equity_advantage'])}")
print(f"  Freed cash flow, reinvested      {money(p['freed_reinvested'])}")
print(f"  --> PATH A total wealth          {money(p['path_a_wealth'])}")
print(f"  --> PATH B Roth IRA @7%          {money(p['path_b_wealth'])}")
print(f"  ROTH ADVANTAGE                   {money(p['advantage_b_over_a'])}")

print()
print("=" * 96)
print("C. SENSITIVITY — does the answer change with market return?")
print("=" * 96)
print(f"{'Return':>7} {'Path A (prepay)':>18} {'Path B (Roth)':>16} "
      f"{'Roth advantage':>16}")
for s in sens:
    print(f"{s['return']*100:>6.0f}% {money(s['path_a']):>18} "
          f"{money(s['path_b']):>16} {money(s['advantage_b']):>16}")

print()
print("=" * 96)
print("D. HORIZON — who is ahead if you sell or refinance at year N?")
print("=" * 96)
print(f"{'Year':>5} {'Path A':>16} {'Path B':>16} {'Roth advantage':>16}")
for h in hor:
    print(f"{h['year']:>5} {money(h['path_a']):>16} {money(h['path_b']):>16} "
          f"{money(h['advantage_b']):>16}")

print()
print("=" * 96)
print("E. 10% DOWN VARIANT (MIP ends after 11 years instead of running 30)")
print("=" * 96)
for row in table10:
    print(f"{money(row['price']):>9} {row['location']:<24} "
          f"down {money(row['down']):>9}  all-in/mo {money(row['total_monthly']):>9}  "
          f"MIP total {money(row['mip_lifetime']):>10} "
          f"(vs {money(row['mip_std_lifetime'])} at 3.5%)")

print()
print("F. CLOSING COSTS — $350,000, Harleysville")
cc = closing_costs(350_000, TAX_RATE["Harleysville 19438"], 337_750)
for k, v in cc.items():
    print(f"   {k:<46} {money(v)}")
print(f"   {'TOTAL (plus 3.5% down = $12,250)':<46} {money(sum(cc.values()))}")

print()
print("G. ALTERNATIVE USES OF THE $6,500/YR")
print(f"   Prepay $541.67/mo instead of $6,500 lump: pays off in "
      f"{alt['prepay_monthly_542']['payoff_years']:.1f} yrs")
b = alt["buy_down_rate"]
print(f"   3 points of rate buydown costs {money(b['cost'])}, cuts rate to "
      f"{b['new_rate']*100:.2f}%, saves {money(b['monthly_saving'], True)}/mo, "
      f"breaks even in {b['breakeven_months']:.0f} months")

print("\nWrote model_output.json")
