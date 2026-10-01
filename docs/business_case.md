# West availability decision

This is a reproducible synthetic case, not a claimed business result. Select revenue and the week of **2024-01-29** in the app.

## Evidence and the business question

Sales attribution identifies a decline in two West products across three channels. The independent operational feed records **three stockout days and a 60% fill rate** for those six cells. No outage, promotion, or price change is recorded in them. The decision engine never reads the scenario ledger to identify this issue.

The company total can rise while these products fall because seasonal demand grows elsewhere. Reviewing only the net company KPI would miss the replenishment question.

## Quantify the decision

The six affected cells are **$2,354.69 below their prior four-week revenue baseline**. This is an exposure estimate, not proven recoverable demand.

| Assumption or result | Default scenario |
| --- | ---: |
| Recoverable share | 50% |
| Potential recovered revenue | $1,177.35 |
| Contribution margin rate | 30% |
| Potential contribution margin | $353.20 |
| Intervention cost | $500.00 |
| Potential value after cost | **−$146.80** |
| Break-even recovery share | **70.8%** |

Under these assumptions, do **not** authorize a $500 replenishment intervention. Ask supply planning to investigate a lower-cost transfer or evidence supporting recovery above 70.8%. At a $200 cost and the same recovery and margin assumptions, potential value becomes **+$153.20**. The sliders expose this tradeoff rather than automatically recommending action whenever an alert appears.

## Execute and verify

**Owner:** supply planning. Confirm inventory and transfer capacity in the affected region/product/channel cells before committing spend. The default baseline assumes the missing volume is still recoverable; delayed orders, substitution, or canceled demand could make that wrong.

**Success measure:** restore fill rate to at least 95%, then track units recovery over the next two complete weeks. Compare seasonal-adjusted results with unaffected cells and verify actual transfer cost and margin. A randomized or otherwise credible untreated comparison is needed to estimate causal impact.

The project calculates a decision scenario and an audit trail. It does not report fictional money saved or realized ROI.
