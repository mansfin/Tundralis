# Tundralis Deck Blueprint v1

## Slide 1 — Executive summary

**Purpose**
- fastest read for a business stakeholder

**Content**
- top 3 priorities
- 1-line explanation for each
- one sentence on overall outcome level
- one sentence on methodology confidence

**Example**
- Policy Value is the top overall priority because it combines high importance, strong impact, and meaningful room to improve
- Enforcement Trust is a second core priority with similarly strong modeled effects
- Policy Clarity remains important and should not be deprioritized, even though its relative impact is slightly lower

---

## Slide 2 — Outcome overview

**Content**
- overall DV score
- distribution
- key segments if relevant
- sample + weighting note

---

## Slide 3 — What matters most

**Chart**
- Shapley importance bar chart

**Purpose**
- explain which attributes account for most variation in the DV

**Headline template**
- [Driver A] and [Driver B] explain the largest share of [DV] differences.

---

## Slide 4 — What moves the outcome most

**Chart**
- ridge impact bar chart

**Purpose**
- show which drivers have the strongest expected effect per 1-point improvement

**Headline template**
- Improvement in [Driver A] and [Driver B] is associated with the largest modeled gains in [DV].

---

## Slide 5 — Priority matrix (classic)

**Default chart**
- x-axis = current performance
- y-axis = importance

**Purpose**
- familiar executive-friendly prioritization view

**Headline template**
- [Driver A] sits in the highest-priority zone due to high importance and below-ceiling performance.

**Notes**
- This chart is communication-first, not the only recommendation engine.
- Use median or meaningful business thresholds for quadrant cutoffs.

---

## Slide 6 — Action matrix (modern)

**Default chart**
- x-axis = current performance
- y-axis = impact
- bubble size = importance

**Purpose**
- show where modeled leverage is strongest while preserving current-state context
- avoid plotting performance against a metric that already embeds headroom

**Interpretation**
- high impact + low performance = best improvement opportunities
- high impact + high performance = protect / maintain strengths
- low impact + low performance = lower-priority cleanup
- low impact + high performance = non-critical strengths / likely lower leverage

---

## Slide 7 — Where to focus first

**Chart or table**
- opportunity score ranking

**Purpose**
- convert analytics into action priority

**Headline template**
- The best near-term opportunities combine meaningful impact with remaining headroom.

**Recommended fields**
- driver
- opportunity score
- importance rank
- impact rank
- performance level
- classification

---

## Slide 8 — Method agreement / confidence

**Content**
- whether Shapley, ridge, and XGBoost broadly agree
- any instability flags
- any nonlinear surprises

**Usage**
- include in appendix by default
- promote to main deck if methods disagree materially

---

## Slide 9 — Recommendations

**Content**
- 3–5 actions
- tied explicitly to priority drivers
- framed as business moves, not statistical artifacts

**Example**
- clarify policy guidance in high-friction moments
- improve enforcement transparency and rationale communication
- reinforce value perception through self-serve resolution experiences

---

## Default visual system

### Communication view
- x = performance
- y = importance

### Action view
- x = performance
- y = impact
- bubble size = importance

### Ranking layer
- opportunity score should be used for rank-ordering and recommendation logic, not as the default chart axis against performance
