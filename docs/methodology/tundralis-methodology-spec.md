# Tundralis Methodology Spec v1

## Purpose

Tundralis identifies and prioritizes key drivers of business outcomes by separating:
1. relative importance
2. modeled impact
3. improvement opportunity
4. nonlinear benchmark checks

The goal is not to force one universal driver rank, but to answer different business questions with the right metric.

---

## Core Framework

### 1. Importance
Importance measures how much each driver contributes to explaining variance in the dependent variable.

**Default method**
- Shapley decomposition of model R-squared

**Use for**
- rank-ordering what matters most
- business-friendly contribution shares
- executive communication
- importance-performance charts

**Interpretation**
- higher importance = stronger contribution to explaining differences in the outcome
- importance is not the same as effect size
- importance is not the same as action priority

---

### 2. Impact
Impact measures how much the dependent variable is expected to change when a driver improves.

**Default method**
- Ridge regression coefficient-based impact estimate

**Use for**
- stable directional effects
- impact ranking
- estimating expected DV lift from a 1-point increase in a driver

**Interpretation**
- higher impact = stronger modeled movement in the outcome per unit change in the predictor
- impact does not necessarily imply high importance
- impact alone does not determine prioritization

---

### 3. Opportunity
Opportunity measures where improvement effort is most likely to generate business value.

**Default method**
- Opportunity score derived from impact, headroom, and confidence

**Conceptual formula**
Opportunity = Impact × Headroom × Confidence

Where:
- Impact = ridge-based modeled DV change
- Headroom = remaining room to improve on the predictor
- Confidence = stability/consensus adjustment

**Use for**
- prioritization
- recommendation generation
- action planning

**Important note**
- opportunity is a ranking and recommendation metric, not a default chart axis
- because headroom/performance is already embedded in opportunity, plotting performance against opportunity can become self-referential

---

### 4. Nonlinear Benchmark
A flexible model is used to determine whether the linear framework is missing major nonlinear structure.

**Default method**
- XGBoost

**Use for**
- predictive benchmark
- interaction detection
- nonlinear discovery
- model cross-checking

**Interpretation**
- XGBoost is a benchmark, not source-of-truth for final business recommendations by itself
- if nonlinear lift is small, linear outputs remain primary
- if nonlinear lift is material, analyst review is required

---

## Metric Hierarchy

### Question: What matters most?
Use **Importance**

### Question: What moves the outcome most?
Use **Impact**

### Question: Where should the business focus first?
Use **Opportunity**

### Question: Are we missing nonlinear structure?
Use **XGBoost benchmark**

---

## Reconciling Metric Disagreement

Different metrics may produce different rank orders. This is expected.

### High importance + high impact
Label: **Core Priority**

### High importance + lower impact
Label: **Foundational Driver**

### Lower importance + high impact
Label: **High-Potential Lever**

### Low importance + low impact
Label: **Lower Priority**

Tundralis does not force one universal ranking across all metrics.

---

## Visual Framework

### Default external chart
- X-axis: current performance
- Y-axis: importance

Purpose:
- familiar executive visualization
- communication shortcut for priority discussion

### Default advanced/action chart
- X-axis: current performance
- Y-axis: impact
- Bubble size: importance

Purpose:
- action-oriented prioritization
- separates current state from modeled leverage
- avoids plotting performance against a metric that already contains headroom

### Opportunity score usage
- use opportunity as a rank-ordering metric
- optionally use it for color, labels, or summary ordering
- do not use it as the default y-axis against performance

Quadrant and bubble charts are communication artifacts, not the sole prioritization engine.

---

## Default Deliverables

For each driver, Tundralis reports:
- mean score
- headroom
- importance
- impact
- max gain
- opportunity score
- confidence/stability
- driver classification

Driver classifications:
- Core Priority
- Foundational Driver
- High-Potential Lever
- Lower Priority

---

## Decision Rules

1. Use importance for explanation
2. Use impact for modeled effect size
3. Use opportunity for prioritization
4. Use XGBoost only as a nonlinear benchmark
5. If methods disagree materially, surface that disagreement rather than hiding it
6. If nonlinear benchmark strongly conflicts with linear outputs, escalate for analyst review
7. Default advanced action visualization is performance × impact, with importance as bubble size
