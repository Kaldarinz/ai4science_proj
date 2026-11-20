# Notation for the paper

Use one name per quantity. This table links paper symbols to the existing
contract in `checks/results_spec.md` and `checks/claims_spec.md`; it does not
introduce new definitions.

| Symbol | Meaning | Source or code field |
| --- | --- | --- |
| $F$ | Pulse fluence (J/cm²) | `get_series`: point `x` when the series `x_quantity` is `fluence` |
| $E$ | Pulse energy (µJ) | `get_series`: point `x` when the series `x_quantity` is `pulse_energy` |
| $x_i$ | Sorted fluence or pulse-energy value at point $i$ | `get_series`: point `x`; never mix quantities within a series |
| $d_i$ | Selected particle-size statistic in nm at point $i$ | `get_series`: `size`; distinguish kind, statistic, weighting and component |
| $e_i$ | Size-error allowance in nm at point $i$ | `get_series`: `size_err`, fixed at 10% or 20% of the selected size for every point |
| $a$ | Current anchor point in the trend classifier | `checks/results_spec.md` §3 |
| $N_{\mathrm{articles}}$ | Fully reviewed articles, including articles with no claim | `results/summary.json`: `articles.n_complete` |
| $N_{\mathrm{own}}$ | Own-data claims, including unassessable ones | `results/summary.json`: `comparison.n_own_data_claims` |

A **claim** is a coded text statement, a **series** is a set of comparable
points from one article and a **pair** links one claim to one candidate
series. The primary and lenient rules use different relative tolerances on every point.
Do not use “power” as a synonym for fluence or energy except in quotations.
