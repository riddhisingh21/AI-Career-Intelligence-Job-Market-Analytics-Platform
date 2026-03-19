# AI Career Intelligence & Job Market Analytics Platform

## Overview

This Streamlit app evaluates how well a resume matches a target job description. It combines resume parsing, ATS-style scoring, semantic similarity, benchmark comparison, role matching, career guidance, market-trend insights, and exportable reports in a lightweight local workflow.

## Features

- Resume parsing for PDF and DOCX files
- ATS match score with visual gauge
- Embedding-based semantic similarity with TF-IDF fallback
- Similarity benchmark comparison between semantic embeddings and TF-IDF baseline
- Dynamic skill extraction from resume and job description text
- Matched and missing skill breakdown
- Section-wise resume analysis for skills, experience, projects, education, and more
- Resume improvement suggestions and report summary
- Job role matching based on detected resume skills
- Career path recommendation with next-step roles and priority skills
- Job market skill trend analysis using role, growth-path, and job-description signals
- Downloadable TXT, CSV, and PDF reports
- Local analysis history stored on the device
- Interactive Streamlit dashboard with charts and skill insights

## Core Modules

- **Resume Parsing System**
- **Resume-Job Matching Engine**
- **Skill Gap Detection**
- **Resume Strength Scoring**
- **Job Role Matching**
- **Career Path Recommendation**
- **Job Market Skill Trend Analysis**
- **Interactive Analytics Dashboard**

## Proposed System Modules

1. **Resume Parsing System**  
   Extracts text from PDF and DOCX resumes for downstream analysis.

2. **Resume-Job Matching Engine**  
   Compares resume content with a target job description using semantic similarity and ATS-style matching.

3. **Skill Gap Detection**  
   Identifies matched skills, missing skills, and improvement priorities.

4. **Resume Strength Scoring**  
   Produces an overall ATS-style score with supporting interpretation.

5. **Job Role Matching**  
   Recommends best-fit roles using the detected resume skill profile.

6. **Career Path Recommendation**  
   Suggests next-step roles and highlights skills needed for career growth.

7. **Job Market Skill Trend Analysis**  
   Infers in-demand skills from role profiles, career paths, and the target job description.

8. **Interactive Analytics Dashboard**  
   Visualizes skill coverage, section scores, role fit, readiness, and market alignment.

## Evaluation and Benchmarking

- The app compares **Embeddings (sentence-transformers)** with a **TF-IDF baseline** for the same resume-job pair.
- A dedicated benchmark panel shows:
  - selected similarity engine
  - embeddings score
  - TF-IDF baseline score
  - score delta between methods
- This adds a lightweight research/evaluation component suitable for final-year-project demos and reports.

## Results and Output Highlights

The system produces a multi-layered output that can be discussed in a project demo or report:

- overall ATS-style match score
- matched and missing skills
- section-wise resume performance
- recommended job roles
- next-step career guidance
- market-aligned and missing trending skills
- similarity benchmark comparison
- downloadable TXT, CSV, and PDF reports

## Project Structure

- `app.py` - Streamlit UI and orchestration
- `analyzer.py` - similarity scoring, benchmark comparison, skill matching, and section-wise resume analysis
- `dashboard_utils.py` - dashboard snapshot helpers for analytics visualizations
- `market_analysis.py` - role matching, career path recommendation, and market-trend analysis
- `skills.py` - skill normalization and extraction helpers
- `pdf_parser.py` - PDF and DOCX text extraction
- `history_store.py` - local SQLite history storage
- `export_utils.py` - CSV and PDF export helpers
- `suggestions.py` - interpretation and recommendation text
- `tests/` - focused unit tests for parsing, analysis, market insights, history, and exports

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   - `python -m pip install -r requirements.txt`
3. Enable **Email/Password** in Firebase Console → Authentication → Sign-in method.
4. Set `FIREBASE_API_KEY` as an environment variable or in `.streamlit/secrets.toml`.
5. To enable Gemini-powered dynamic analysis, set `GEMINI_API_KEY` as an environment variable or in Streamlit secrets.
6. Start the app:
   - `python -m streamlit run app.py`

## Usage

1. Sign in or create an account using the Firebase email/password screen.
2. Upload a resume in PDF or DOCX format.
3. Paste the target job description.
4. Click **Analyze Resume**.
5. Review the ATS score, primary analysis engine, and the benchmark comparison panel.
6. Explore matched/missing skills, section-wise analysis, and the analytics dashboard.
7. Review recommended job roles, career path suggestions, and market-trend skill insights.
8. Download the report in TXT, CSV, or PDF format.
9. Revisit recent analyses from the sidebar history for the signed-in account.

## Notes

- The embedding model may take longer on the first semantic analysis while it loads or downloads.
- Firebase email/password authentication requires `FIREBASE_API_KEY` and the Firebase Authentication Email/Password provider to be enabled.
- Password reset emails are sent through Firebase from the login screen.
- When `GEMINI_API_KEY` is configured, the main analysis flow uses Gemini for a more dynamic score, skills assessment, role matching, and recommendations.
- If Gemini is unavailable or the API key is missing, the app falls back to the existing local analysis pipeline.
- If the embedding model is unavailable, the app automatically falls back to TF-IDF scoring.
- Analysis history is stored locally in `analysis_history.db` and scoped by signed-in email.
- The benchmark panel is intended as an evaluation aid, not as a substitute for real-world hiring decisions.

## Testing

Run the focused unit tests with:

- `python -m unittest tests.test_firebase_auth tests.test_gemini_analysis tests.test_dashboard_utils tests.test_market_analysis tests.test_semantic_similarity tests.test_analyzer tests.test_pdf_parser tests.test_suggestions tests.test_history_store tests.test_export_utils tests.test_evaluation_utils`

