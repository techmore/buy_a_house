# buy_a_house

An FHA first-time homebuyer analysis for **Harleysville**, **Collegeville**, and
**Upper Black Eddy**, Pennsylvania (Montgomery & Bucks County).

**📖 Read the guide:** https://techmore.github.io/buy_a_house/

---

## What's here

| File | Purpose |
|---|---|
| [`FHA_Homebuyer_Guide.md`](FHA_Homebuyer_Guide.md) | The full guide — 9 sections |
| [`model.py`](model.py) | The financial model behind every number |
| [`model_output.json`](model_output.json) | Computed results, machine-readable |
| [`index.md`](https://techmore.github.io/buy_a_house/) | GitHub Pages landing page |

## Reproduce the numbers

```bash
python3 model.py
```

Regenerates `model_output.json` and prints the full report: purchase-power tables,
amortization, closing costs, income qualification, and the prepay-vs-Roth comparison.

## What the guide covers

1. **The 60-second version** — headline findings
2. **How FHA financing works in 2026** — MIP structure, loan limits, the 10%-down trap
3. **The neighborhoods** — live listings, tax rates, what your money buys
4. **Monthly payment estimates** — five price points across three areas
5. **How to avoid closing costs** — seven concrete strategies
6. **The 30-year mortgage in full** — balance and equity over time
7. **$6,500/year: prepay the mortgage or fund a Roth IRA?** — the crossover analysis
8. **Action checklist**
9. **Caveats and confidence**

## Headline findings

- **Upper Black Eddy has the lowest property tax** (0.98% vs. 1.36% / 1.45%) but is
  **not price-cheap** — its ZIP median is ~$562,000 and most sub-$250k inventory is
  vacant land.
- **Harleysville has the best affordable selection** — six listings under $400,000.
- **The Roth-vs-prepay decision flips at a ~6.2% market return.** Below that,
  prepaying the mortgage wins; above it, the Roth does.
- **2026 FHA limit for both counties is $630,200** — the buyer's real constraint is
  income and cash, not the loan cap.

## Caveats

Educational analysis only — not a loan commitment, tax advice, or a guarantee.
Rates, limits, tax rates, and program terms change. Listing data was retrieved
**September 10, 2026** and is perishable. Always verify with a licensed lender and
with [PHFA](https://www.phfa.org), [HUD](https://www.hud.gov), and the
[CFPB](https://www.consumerfinance.gov).
