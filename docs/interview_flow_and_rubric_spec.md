# Capital One Case Interview — Agent Interaction Flow & Evaluation Rubric

> **How to use this file:** paste this whole document to Claude Code along with the instruction:
> "Please use this as the design spec for the interviewer agent's stage logic and the evaluator agent's scoring rubric. Update the agent code so the interviewer gates information by stage instead of releasing everything at once."

---

## Part 1 — Interaction Flow (what the interviewer agent should do at each stage)

The core fix: **the interviewer should not dump the full case (background + clarifying answers + all data) in one message.** Real interviews are gated — the candidate has to actively do something before the next layer of information is unlocked. The interviewer agent should track an internal `stage` variable and only reveal what belongs to that stage.

### Stage 0 — Present the case background only
- Interviewer gives: the company situation + the business question (e.g. "a sports company is deciding whether to lease a stadium — is it profitable?").
- Interviewer does **NOT** yet reveal: clarifying answers, framework hints, or any numbers.
- Interviewer waits for the candidate's recap before moving on.

### Stage 1 — Candidate Recap (gate: must happen before Stage 2)
- Expected candidate behavior: restate the situation and the objective in their own words, concisely (roughly 30–60 seconds of speech).
- Template pattern to detect: *"Just to make sure we're aligned — [company] is [doing X], and the goal is to [evaluate/decide Y]. Is that right?"*
- **Agent logic:** if the candidate skips this and jumps straight to asking numbers or giving a framework, the interviewer should gently redirect: *"Before we go further, can you first summarize the situation back to me?"* — don't just silently allow the skip.
- If the candidate's recap misses or misstates the actual objective, the interviewer should correct it before continuing (this is a common real failure mode — solving the wrong problem).
- Once the recap is correct, the interviewer should briefly confirm ("That's right.") and then **stop talking** — no inviting or prompting for clarifying questions (see Stage 2's candidate-initiated rule).

### Stage 2 — Clarifying Questions (candidate-initiated and optional — never prompted by the interviewer)
- Candidate should ask one or more targeted questions. Typical directions are:
  - **Goal/success metric** — break even? hit a margin target? maximize something specific?
  - **Scope** — one product/region vs. whole business?
  - **Time horizon** — single year vs. multi-year?
  - These are **examples for the interviewer's internal judgment only, not a checklist and never something to say out loud** — a candidate who asks a single sharp, on-topic question should be allowed to move on; they should never be held at this gate just because they didn't also ask about scope or time horizon.
- **Agent logic:** the interviewer must never proactively ask "Do you have any clarifying questions?" or hint at what topics are worth asking about — real interviewers wait silently and only react to what the candidate initiates. Two legitimate candidate paths, and the interviewer never pushes toward either:
  - The candidate asks a question → answer only what's asked, don't volunteer extra data. If a question is too vague/broad ("tell me everything about the company"), push back and ask them to be specific. Keep answering further questions for as long as they keep asking (roughly up to 3 is typical, not a hard cap) — don't require covering more topic categories. Once answered, advance to Stage 3 the moment the candidate signals readiness or starts giving a framework.
  - The candidate skips straight to a framework, asking nothing → that's a legitimate real-interview choice; accept it and move to Stage 3 without stopping to ask if they have questions first.
  - Only intervene if the candidate stalls, asks something unanswerable from the case, or clearly over-asks (5+ scattered questions): *"Let's move on to how you'd structure your analysis."*

### Stage 3 — Framework Presentation (candidate-initiated — gate: before any numbers are given, and before any formula from the interviewer)
- Candidate should present a structure **before** requesting numbers — typically:
  - **Financial** (revenue drivers + cost drivers) — this should be the majority of the depth
  - **Customer** (segmentation, price sensitivity, churn) — brief
  - **Market/Competition** (growth, seasonality, competitors) — brief
- **Agent logic:** if the candidate asks for numbers before stating any framework, the interviewer should stop them: *"Before I give you the numbers, how would you structure this analysis?"* The interviewer must never suggest, list, or hint at these framework categories itself — it only evaluates whatever structure the candidate proposes on their own.
- If the framework is reasonable but Financial isn't clearly the lead bucket, the interviewer can accept it but the evaluator should note this as a minor gap (see rubric below).
- When transitioning into Stage 4 (presenting the first sub-question + its data), the interviewer must not also state or hint at the equation/formula needed to solve it — that has to come from the candidate in Stage 4.

### Stage 4 — Quantitative Analysis (all data for a sub-question given up front, not requested piece by piece; equation always comes from the candidate)
- Each of this case's sub-questions already comes with its full data set written into the question itself (see the case files). The interviewer should give the sub-question **and all of its data, together, in one message** as soon as the candidate reaches it — this is realistic to how Capital One case questions are actually phrased, and the point of this stage is testing the candidate's ability to structure and narrate a calculation, not to make them fish for inputs.
- The candidate does not need to request data one field at a time, and the interviewer never states or hints at the equation itself. The candidate's job is to:
  - Propose the equation first ("Profit = Revenue − Fixed Cost − Variable Cost, and Revenue = Price × Volume") — unprompted, in their own words
  - Plug in the numbers the interviewer already gave them, labeling each one as they use it
  - State assumptions explicitly if a number isn't given
  - Narrate the calculation logic out loud, not just announce a final number
- **Agent logic — this is the core adaptive-follow-up moment:**
  - If the candidate skips straight to a final number with no visible logic, the interviewer should ask them to walk through it: "Can you walk me through how you calculated that?" — not accept or reject the number yet.
  - If the candidate's math is wrong → interviewer should point to *where* the error likely is without just giving the answer ("Can you double-check that revenue-share calculation?"), not simply reveal the correct number.
  - If the candidate got a correct baseline but the case supports a follow-up variant (e.g., "what if attendance were 85% instead of 75%?" or a break-even question), the interviewer should ask it.
  - If the candidate glossed over a stated assumption without justifying it, interviewer should probe: "Why did you assume that?"

### Cap on repeated redirects (applies to every gate above)
- The interviewer must never redirect/follow-up on the exact same gate or sub-question more than 3 times in a row — looping indefinitely on one sticking point isn't realistic.
- On the 3rd unresolved attempt: for a soft/qualitative gate (recap accuracy, clarifying-question specificity, framework shape), the interviewer should accept the closest reasonable version, briefly name the gap, and advance anyway rather than asking a 4th time. For a hard, gradable gate (Stage 4 math, a repeated fundamental error), the interviewer keeps grading honestly — the same-question fail rule (Part 5, item 2) already ends the case after a 4th consecutive wrong attempt, so no new redirect angle is needed beyond that point.

### Stage 5 — Recommendation (gate: expects CSR structure)
- Candidate should give: **Conclusion → Supporting data → Risks → Next steps**, roughly 60–90 seconds.
- **Agent logic:** if the candidate gives only a conclusion with no risks/next steps, the interviewer should ask: *"What risks would you flag with this recommendation?"* rather than ending the interview outright.
- Interviewer should challenge the recommendation at least once (real interviewers almost always push back), e.g.: "What if the lease terms weren't negotiable — would you still recommend this?"

---

## Part 2 — Evaluation Rubric (for the evaluator agent)

The evaluator agent should score each completed case on these five dimensions. Each dimension should get a short score (e.g. 1–4) plus **one concrete, specific comment** — never just "good job" or "needs work."

| Dimension | What "strong" looks like | What "weak" looks like |
|---|---|---|
| **1. Recap & Objective Alignment** | Concise, correctly identifies the real decision to be made, phrased as a confirming question | Skipped entirely, or restates the story without naming the actual objective |
| **2. Clarifying Questions** | 2–3 sharp questions covering goal/scope/time-horizon-type gaps | Zero questions, or vague/scattered questions (5+, unfocused) |
| **3. Framework Structure** | Financial-first structure with Revenue/Cost breakdown; Customer & Market present but brief | Framework missing entirely, or all three buckets given equal unfocused depth, or jumped to numbers with no framework |
| **4. Quantitative Execution** | States equation before calculating, labels numbers, flags assumptions, correct math, handles the follow-up/sensitivity question well | Silent number-crunching with no stated logic, unlabeled figures, unstated assumptions, or unresolved math error |
| **5. Recommendation (CSR)** | Clear conclusion, ties back to the specific numbers calculated, names a real risk, gives a concrete next step, handles the interviewer's pushback well | Conclusion only, generic risk ("market could change"), or caves immediately when challenged instead of defending the logic |

**Evaluator output format** (what gets shown to the user after each case):

```
Case: [name]
1. Recap:            [score] — [specific comment]
2. Clarifying Qs:    [score] — [specific comment]
3. Framework:        [score] — [specific comment]
4. Quant Execution:  [score] — [specific comment]
5. Recommendation:   [score] — [specific comment]

Top 2 things to improve next time:
- [specific, actionable point]
- [specific, actionable point]
```

---

## Part 3 — What this changes about the interviewer agent's state design

For Claude Code: the interviewer agent needs a `current_stage` field in its state (0–5 as above), and its system prompt/logic should include a rule like:

> "Only reveal information appropriate to `current_stage`. Do not advance `current_stage` until the candidate has produced the expected behavior for the current stage (recap, clarifying questions, framework, etc.) — if they skip ahead, redirect them back to the current stage's expectation instead of complying."

This is the mechanism that closes the gap you identified: the interviewer becomes a **gatekeeper of information**, not a script-reader.

---

## Part 4 — Judging Candidate Expansions Outside the Core Framework

Candidates will sometimes raise points that go beyond the core financial framework (e.g. seasonality, regulatory risk, brand perception, competitor response). These can't be pre-enumerated into a checklist — the agent needs to reason about each one live, using the specific case's numbers as ground truth. Use these three judgment principles:

1. **Materiality** — does this point plausibly change the profit/decision math in *this specific case*, or is it true-but-inert decoration? A point that would shift the recommendation if quantified is valuable; one that sounds relevant but doesn't actually move any number in this case is not.
2. **Proportionality** — is the time/depth spent on this point reasonable? A brief (roughly 30-second-equivalent), well-placed mention of something outside the core numbers is normal and often reflects good business breadth. The same point expanded into a long detour away from the quantitative analysis is a red flag — real interviewers penalize losing the thread, not raising the point itself.
3. **Justification vs. name-dropping** — did the candidate explain *why* this matters here specifically, or did they just list buzzwords ("also market dynamics, also brand, also...") with no reasoning attached? Reward the former; treat the latter as filler, not insight.

**Evaluator guidance:** reward expansions that are material, proportionate, and justified. Do not penalize brief, well-reasoned detours just because they fall outside the core Financial/Customer/Market structure — real case interviews value this kind of judgment. Do flag expansions that are long, ungrounded in the case's numbers, or presented as a list of buzzwords with no explanation.

---

## Part 5 — Addenda from Phase 1 browser testing

These were added after the candidate ran the stage-gated interviewer in the browser and found gaps:

1. **Grounding.** Every case file's `## Context` section must state an explicit business objective / decision question (not just the company situation) — without it, the interviewer has nothing to anchor to and may invent one (e.g. hallucinating "production capacity" as the goal for a case that's actually about profitability). The interviewer's system prompt also carries an explicit rule: any objective, number, or term it references must be traceable to the case content, never invented.
2. **Same-question fail rule.** If the candidate gets the same question wrong more than 3 times in a row (4th consecutive wrong attempt), the case ends immediately as a fail, with a short note naming the stage/section that caused it. This is tracked by having the interviewer tag every reply with a grading status (`correct` / `incorrect` / `na`) against whatever gate/question is currently active, in addition to the stage number — the app (not the model) counts consecutive `incorrect` tags and ends the case when the threshold is crossed.
3. **Cap on repeated redirects.** The interviewer must not loop indefinitely on one sticking point — see "Cap on repeated redirects" above (max 3 redirects on the same gate, then either advance with a noted gap, for soft gates, or let the same-question fail rule take over, for hard gates).
4. **No proactive clarifying-question prompting.** Stage 2 is candidate-initiated only — the interviewer never asks "Do you have any clarifying questions?" and never hints at what to ask about. Skipping clarifying questions entirely and going straight to a framework is a legitimate candidate choice.
5. **No proactive framework/equation hints.** Stages 3 and 4 are candidate-initiated — the interviewer never suggests framework categories or states/hints at an equation; it only evaluates what the candidate proposes on their own.


