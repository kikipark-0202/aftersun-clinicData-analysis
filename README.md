# AfterPatch+ Privacy Scorecard

> A weighted scoring algorithm that ranks STI testing clinics by privacy, clinical capability, cost, accessibility, and medication availability — personalized to each user's priorities and gender.

## Why This Exists

After surveying **374 respondents** across two rounds, we found that **82% of 18-29 year olds in Korea never visit a hospital for STI testing**, primarily due to social stigma and privacy concerns. The #1 action anxious users take — internet searching — is also the #2 cause of their anxiety.

There is no existing tool that helps users compare testing facilities based on *how private the experience will be*. This scorecard fills that gap.

## How It Works

### Scoring Algorithm

Each clinic is scored across 6 categories with user-adjustable weights:

| Category | Default Weight | What It Measures |
|----------|---------------|-----------------|
| Privacy | 30% | Anonymous testing, real-name requirements, booking method, results delivery |
| Clinical | 25% | STI types covered, doctor gender availability, insurance, home kits |
| Cost | 15% | Minimum test price (inverse normalized — cheaper = higher score) |
| Accessibility | 10% | Weekend hours, online booking, transit proximity |
| Medication | 10% | PEP availability, PrEP consultation, on-site pharmacy |
| Trust | 10% | User reviews (placeholder for v2) |

### Gender-Aware Filtering

- **Female-only clinics** (e.g., 포유문산부인과) are excluded from male user rankings
- **Male-only STI tests** (e.g., gonorrhea testing at certain public health centers) reduce the effective STI count for female users
- This was discovered during data collection and reflects real-world access constraints

### Data Pipeline

```
Raw Excel (18 clinics × 28 columns)
  → Y/N standardization ("Only HIV" → 0.5 partial score)
  → Price parsing (free-text Korean → min integer)
  → Manual corrections (range notation: "2-3만원" → 20000)
  → Min-max normalization (0-1 scale)
  → Weighted composite scoring
  → Gender-conditional filtering
  → Interactive dashboard
```

### Key Design Decision: v1 Minimum Price

Price scoring currently uses the minimum available test price. This is a deliberate v1 simplification. The actual cost depends on which STI the user is concerned about (blood test vs. urine test vs. swab), which will be handled by the AI chatbot's triage flow in Phase 2.

## Data Sources

- **Primary**: Manual data collection from clinic websites, Naver Map listings, and direct phone verification (structured phone interviews with 20 clinics)
- **Methodology**: Each clinic was verified across Tier 1 (online research), Tier 2 (phone calls with standardized script), and Tier 3 (public health center directories)
- **Last verified**: April 2026

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project Context

This is Phase 1 of [AfterPatch+](https://github.com/kikipark-0202/afterpatch-survey-analysis), a digital health platform addressing STI window-period anxiety. The project pivoted from a wearable hardware concept to a software platform based on user research findings.

**Phase 1** (this repo): Privacy Scorecard Algorithm + Dashboard  
**Phase 2** (planned): RAG-powered AI Chatbot for guided consultation  
**Phase 3** (planned): Full platform integration with testing timeline  

## Tech Stack

Python, pandas, Streamlit, Plotly, openpyxl

## Author

Kihyun Louis Park · Kyung Hee University  
B.S. Media Technology · B.A. Digital Design (UX)
>>>>>>> 78ab4ae (Initial commit)
