# Aftersun: Synthetic Clinic Data Generation

A pipeline that expands 18 real STI testing clinics in Seoul into 500 synthetic 
clinics, preserving the statistical properties and domain relationships of the 
original data.

**What I focused:** Addressing the small-sample limitation(n=18) of privacy-sensitive 
healthcare data.

## Problem

Real data on STI testing clinics is mmostly privacy-sensitive. With only 18 
real clinics, meaningful statistical analysis or ML is not feasible. This project 
generates a larger synthetic dataset that preserves the original's structure.

## Approach

Each attribute is generated **conditionally on clinic type**, avoiding 
contradictions like a "free public health center priced at 80,000 KRW."
Three generation strategies(Statistical, Proportional, Domain-based) are used depending on data characteristics:

1. Statistical(`price`): Normal distribution per type (mean/std), clipped to realistic floor
2. Proportional(`anonymity`, `weekend hours`, `online booking`): Sampled by each type's observed proportions
3. Domain-based(`STI count`): Verified domain knowledge

## Key Decisions

- **Domain constraints over raw data:** STI counts were inconsistently recorded 
  in the source (often blank while test types were listed in detail). Rather than 
  using unreliable values, I applied verified domain knowledge: e.g. urology/OB-GYN cover 13
  types (12 STIs + HIV), while public health covers only 3-4.
- **Preserving real ranges:** Price ranges (e.g. 10,000~20,000) kept both 
  endpoints rather than averaging, avoiding invented values.
- **Reproducibility:** Fixed random seed(n=42) ensures identical output on every run.

## Limitations & Future Development

- Small source sample (n=18); per-type samples are smaller still (OB-GYN: n=3).
- **Sampling bias:** larger hospitals are over-represented, which may inflate 
  attributes like weekend availability for OB-GYN clinics.
- Synthetic data reproduces the source's structure — including its biases.

## Files

- `notebook.ipynb` — full pipeline (loading → parsing → EDA → generation → validation)
- `data.py` — preprocessing (cleaning, parsing)
- `synthetic_clinics.csv` — generated dataset (500 clinics)
