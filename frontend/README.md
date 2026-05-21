from pathlib import Path

readme_content = """

# ResuMatrix Frontend

ResuMatrix is an intelligent resume ranking platform that takes a job description and a set of resumes, and ranks the resumes based on their fit to the job. This frontend, built using **Streamlit**, is integrated with Supabase for authentication and Google Cloud Storage (GCS) for file handling.

---

## Directory Structure

```
/                              
-- src/                                         # Root 
-- frontend/                                    # Frontend directory
    -- app/ 
        -- core/
             -- config.py                       # configuration file for environement variable setup                
    -- utils/                                   # Folder containing any utility functions
         -- create_download_link.py             # Utility function for frontend UI purposes
    -- streamlit_app.py/                        # main file for streamlit UI
    -- supabase_auth.py                         # authentication file for streamlit integration with supabase
    -- text_extraction.py                       # extract text from job description for preview
    -- .env                                     # contains all environment variables, api keys and dependencies
    -- README.md                                # documentation file for frontend
    -- Dockerfile                               # Frontend dockerfile              
```

---

## Features

### User Authentication
- Integrated with **Supabase Auth** for secure sign-up and login.
- Authenticated users are persisted in session state.

### Job Description Upload & Parsing
- Accepts job descriptions via:
  - Text input
  - File upload (PDF, TXT, DOCX)
- Uses a Gemini LLM to modularize and structure the JD.

### Job Description Refinement
- Users can describe desired modifications to the JD.
- A refined version is regenerated using the LLM.

### Resume Upload & Preprocessing
- Users can upload resumes as a `.zip` containing PDFs.
- System filters out irrelevant/system files and stores valid PDFs.
- Resumes are uploaded to Supabase and stored in a GCS bucket under the corresponding job ID.

### Resume Classification
- A backend pipeline classifies the resumes as good fit or no fit.
- A supervised XGBoost model classfies the resume given a job description.
- Changes the status of all the resumes and sends over the good fit resumes for the ranking task.

### Resume Ranking
- A backend pipeline ranks the resumes asynchronously.
- The frontend polls the API until processing is complete.
- Displays resumes in ranked order with public preview links.

### Feedback Collection *(if enabled)*
- Users can label top resumes as `Good Fit` or `No Fit` to collect feedback for retraining.

---

## Setup & Running

### 1. Prerequisites

- Python 3.9+
- Docker
- `gcp_secret_key.json` file with access to your Google Cloud Storage bucket
- `.env` file with the following keys:

### Tech Stack

- Frontend: Streamlit
- Auth: Supabase
- Storage: Google Cloud Storage
- Backend: FastAPI (external service)
- LLM Processing: Gemini via internal API
- Resume Ranking: Machine Learning models orchestrated via Airflow (backend service)

### Screenshots of the frontend:

![ResuMatrix Job Description Page](/frontend/res/resumatrix_job_description.png)
![ResuMatrix Resume Ranking Page](/frontend/res/resumatrix_resumes_dashboard.png)
![ResuMatrix Feedback Page](/frontend/res/resumes_feedback.png)

