# Draft issue: spousal add-on in `compute_social_security_benefits` — first year cut when the later claim predates the plan; start depends on person order

Fork note (2026-10-19). Found by the fork's earnings-test no-op grid (Phase 5 steps 1-2
review): a monthly rebuild of the SS streams disagreed with `compute_social_security_benefits`
in two cases, and in both the monthly rebuild was right. Checked on stock upstream `dev`
`4932cb9` with `fork-notes/issue-spousal-start-repro.py` (output below from real runs). No
upstream example is affected: none has a spousal add-on with both claims before 2026, and
none enters a claiming age below the eligibility reset (checked on the 18 example TOMLs).
The fork applies the patch (`socialsecurity.py`, `tests/ss/test_spousal_start_fork.py`);
when upstream fixes it, take theirs. For the user to file.

---

**Title:** Spousal benefit: first plan year cut when both spouses already collect; start month depends on which spouse is listed first

`compute_social_security_benefits` builds the spousal add-on in `_add_spousal_benefit`:

```python
latest_claim_year = float(np.max(yobs + (mobs - 1) / 12 + ages))
...
payment_claim_year = latest_claim_year + 1 / 12
ns2 = max(0, int(payment_claim_year) - thisyear)
...
spousal_in[i, ns2:nd] += spousal_amount * spousal_factor
spousal_in[i, ns2] -= spousal_amount * spousal_factor * (payment_claim_year % 1.0)
```

1. **Later claim before the plan.** When `payment_claim_year` is before `thisyear`, `ns2` is
   clamped to 0 but the partial-year subtraction still applies, so the first plan year loses
   `payment_claim_year % 1.0` of the spousal amount. The own benefit has the guard
   (`if payment_start_n >= 0 and ns < nd: own_in[i, ns] *= frac`); the spousal one does not.
2. **Order of the eligibility reset.** `compute_social_security_benefits` resets `ages[i]`
   (e.g. 62.0 → 62y1m for someone born after the 2nd) inside the same loop that calls
   `_add_spousal_benefit` for person `i`, and `_add_spousal_benefit` reads *both* ages. When
   person 0 receives the add-on and person 1 is the later claimer with an age below the reset,
   person 0's spousal start is read from person 1's un-reset age: one month early. Listing the
   couple the other way round gives a different result.

Repro (`thisyear=2026`, horizons 25):

- Case 1: PIAs 3000 / 800, born 1961-01-15 and 1962-05-15, both claim at 62 (the second is
  reset to 62y1m, June 2024). Person 1's 2026 benefit should be 12 × (800 × 0.704167 + 700 ×
  0.654167) = 12,255.00.
- Case 2: PIAs 1000 / 3000, born 1964-03-15 (claims 62y1m) and 1966-05-15 (enters 62.0, reset
  to 62y1m = June 2028). The auxiliary's 2028 benefit should be 8,450 + 500 × 0.770833 × 6
  (July-December) = 10,762.50, whichever spouse is listed first.

Stock `dev` `4932cb9`:

```
1. person 1, 2026: 9,507.50   expected 12 x (own 563.33 + spousal 457.92) = 12,255.00
2. auxiliary, 2028: listed first 11,123.61, listed second 10,762.50   expected 10,762.50
```

With the patch below:

```
1. person 1, 2026: 12,255.00   expected 12 x (own 563.33 + spousal 457.92) = 12,255.00
2. auxiliary, 2028: listed first 10,762.50, listed second 10,762.50   expected 10,762.50
```

`tests/ss` and `tests/plan` on patched stock `dev`: 448 passed.

Patch (against `dev` `4932cb9`; also in `fork-notes/issue-spousal-start.patch`): guard the
partial-year subtraction like the own benefit's, and reset every age in a loop of its own
before building the streams.

```diff
diff --git a/src/owlplanner/socialsecurity.py b/src/owlplanner/socialsecurity.py
index ca74eab..1d5464e 100644
--- a/src/owlplanner/socialsecurity.py
+++ b/src/owlplanner/socialsecurity.py
@@ -379,7 +379,9 @@ def _add_spousal_benefit(spousal_in, i, nd, spousal_amount, fra, yobs, mobs, age
         return  # Spousal benefit would start at or after the end of entitlement.
     spousal_factor = getSpousalFactor(fra, claim_age, bool(tobs[i] == 1))
     spousal_in[i, ns2:nd] += spousal_amount * spousal_factor
-    spousal_in[i, ns2] -= spousal_amount * spousal_factor * (payment_claim_year % 1.0)
+    if int(payment_claim_year) >= thisyear:
+        # Partial first year only when the first spousal check falls inside the plan.
+        spousal_in[i, ns2] -= spousal_amount * spousal_factor * (payment_claim_year % 1.0)
 
 
 def validate_survivor_claim_age(survivor_claim_age):
@@ -676,17 +678,20 @@ def compute_social_security_benefits(
     fras = getFRAs(yobs, mobs, tobs)
     spousalBenefits = getSpousalBenefits(pias)
 
-    own_in = np.zeros((N_i, N_n))
-    spousal_in = np.zeros((N_i, N_n))
+    # Eligibility: born on 1st or 2nd can claim in their birthday month (or prior for 1st).
+    # Every age is reset before any stream is built: the spousal start reads both ages.
     for i in range(N_i):
-        # Eligibility: born on 1st or 2nd can claim in their birthday month (or prior for 1st).
-        # Factor shift: only born on 1st attains age one month early, warranting +1/12 SSA age.
         bornOnFirstDays = tobs[i] <= 2
-        bornOnFirst = tobs[i] == 1
         eligible = 62 if bornOnFirstDays else 62 + 1 / 12
         if round(ages[i] * 12) < round(eligible * 12):
             ages[i] = eligible
 
+    own_in = np.zeros((N_i, N_n))
+    spousal_in = np.zeros((N_i, N_n))
+    for i in range(N_i):
+        # Factor shift: only born on 1st attains age one month early, warranting +1/12 SSA age.
+        bornOnFirst = tobs[i] == 1
+
         payment_start_n, frac = _payment_start(yobs[i], mobs[i], ages[i], thisyear)
         ns = max(0, payment_start_n)
         nd = int(horizons[i])
```
