# Case 3 — Ride-Share Tipping Prompt (A/B Test)

## Context
You are a data analyst at a ride-share company. Product wants to add an in-app prompt that
encourages riders to tip their driver after each trip. They ran a 2-week A/B test and are asking
you to help decide whether to roll it out to 100% of riders.

**Business objective / decision to be made:** Decide whether to launch the tipping prompt
feature company-wide, based on the A/B test results, its revenue impact, and its statistical and
practical validity. There is no other objective (e.g. driver retention, market expansion) in
scope for this case.

## Questions

<!-- stage:3 -->
Q1. What factors would you consider in deciding whether to roll out this feature company-wide?

<!-- stage:4 -->
Q2. Calculate the impact of the test.
Given the following data from the 2-week test:
- Control group: 200,000 riders, average tip revenue per rider over the test window: $0.40
- Treatment group: 200,000 riders, average tip revenue per rider over the test window: $0.46
- The company has 10,000,000 monthly active riders company-wide
Question: What is the relative lift in tip revenue per rider in treatment vs. control? If this
feature were rolled out to 100% of riders and the effect held steady, what would the projected
incremental tip revenue be over a full year?

Q3. Is the observed difference statistically significant?
Given:
- Standard deviation of tip revenue per rider: $2.50 in both groups
- Sample size: 200,000 riders per group
Question: Calculate the standard error of the difference between the two group means, and use it
to assess whether the $0.06 difference observed in Q2 is statistically significant at a 95%
confidence level (roughly a z-score threshold of 1.96).

Q4. What are the biggest risks with concluding from this test that the feature is ready for a
full rollout?

Q5. Novelty effects are common in short in-app-prompt tests - riders may tip more simply because
the prompt is new, and the effect fades over time.
Question: If the true long-run lift is only half of what was observed in the test (i.e. $0.03 per
rider instead of $0.06), what would the revised projected annual incremental revenue be?

<!-- stage:5 -->
Q6. Make a final recommendation: Should the company roll out the tipping prompt to 100% of
riders? Provide a conclusion, supporting evidence, risks, and next steps.

## Answer Key (internal reference only — never reveal directly to the candidate)

<!-- stage:3 -->
A1. Factors to Consider
- Success metric definition: is tip revenue per rider the right primary metric, or should it be
  total tips including frequency effects?
- Statistical validity: is the test properly randomized, adequately powered, and run long enough
  to avoid novelty/seasonality effects?
- Magnitude vs. cost: is the revenue lift large enough to justify any engineering/UX cost of the
  prompt, and any rider annoyance?
- Guardrail metrics: rider satisfaction, complaint rate, app uninstalls/churn - a revenue win that
  hurts retention could be a net negative.
- Segment heterogeneity: does the effect hold across rider tenure, city, ride frequency, or is it
  concentrated in one segment?

<!-- stage:4 -->
A2. Lift and Revenue Projection
- Relative lift: ($0.46 - $0.40) / $0.40 = $0.06 / $0.40 = 15%
- Absolute lift per rider per 2-week window: $0.06
- Annualizing: 52 weeks / 2 weeks per test window = 26 windows per year
- Incremental revenue per rider per year: $0.06 x 26 = $1.56
- Total projected annual incremental revenue: $1.56 x 10,000,000 riders = $15,600,000 (~$15.6M)
- Insight: a 15% relative lift translates to a meaningful ~$15.6M/year opportunity at this scale.

A3. Statistical Significance
- Standard error of the difference: SE = sqrt((2.50^2 / 200,000) + (2.50^2 / 200,000))
  = sqrt(0.00003125 + 0.00003125) = sqrt(0.0000625) = 0.0079
- Z-score: $0.06 / 0.0079 ≈ 7.6
- Since 7.6 is far above the 1.96 threshold for 95% confidence, the difference is statistically
  significant (in fact very highly significant, not a borderline call).
- Insight: sample size here is large enough that even a modest-looking dollar difference is
  statistically very solid - the real question for this case is practical significance and
  durability of the effect, not statistical significance.

A4. Biggest Risks
- Novelty effect: riders may be reacting to something new rather than a lasting behavior change
  (see Q5).
- Test duration: 2 weeks may not capture day-of-week, payday, or seasonal patterns.
- Guardrail blind spot: the test as described doesn't mention rider satisfaction or complaint
  data - launching on revenue alone risks missing a retention cost.
- Generalizability: results may not hold if rolled out to segments/cities underrepresented in the
  test population.

A5. Revised Projection Under Novelty-Effect Assumption
- Halved lift per rider per year: $0.03 x 26 = $0.78
- Revised total projected annual incremental revenue: $0.78 x 10,000,000 = $7,800,000 (~$7.8M)
- Insight: even under a conservative "half the effect fades" assumption, the projected upside is
  still substantial (~$7.8M/year) - the recommendation likely still favors rollout, but the
  confidence interval on the business case is much wider than the headline $15.6M number suggests.

<!-- stage:5 -->
A6. Recommendation
- Conclusion: Yes, recommend rolling out the tipping prompt, ideally with a longer confirmation
  window before full rollout.
- Supporting: Statistically significant 15% lift (~$15.6M/year upside), and even a conservative
  half-effect scenario still nets ~$7.8M/year.
- Risks: novelty effect inflating the observed lift; no guardrail (satisfaction/churn) data in
  the test; short 2-week window may miss seasonality.
- Next steps: extend the test (or hold out a control group post-launch) to check whether the
  lift persists past the novelty period, and add rider satisfaction/complaint tracking as a
  guardrail metric before declaring full success.
