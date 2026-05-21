## Overview

ResuMatrix is an Agentic AI-based Resume Analysis and Ranking Application. 

This project is part of the coursework for IE 7374: Machine Learning Operations.
This project is part of the coursework for IE 7374: Machine Learning Operations.

## Introduction


Our resume-job matching pipeline is designed to automate the end-to-end process of extracting, processing, and analyzing job descriptions and resumes. Built using Apache Airflow, our pipeline orchestrates various tasks such as loading data, cleaning, preprocessing using natural language processing (NLP) techniques, and applying machine learning models to determine the suitability of a resume for a given job description.

Contributors: **Team-20** of IE 7374 MLOps Spring 2025 batch

-   Ashish Annappa Magadum
-   Kishan Sathish Babu 
-   Nishchith Rao Palimar Raghupathi
-   Pranay Saggar
-   Shailendra Tripathi

## Project Structure

```
/                          # Root   
-- src/                    # This has all the model training files and preprocessing code  
-- data_pipeline/          # Airflow data pipeline directory which has the dags to run deployment, retraining and training pipeline  
-- backend/                # This is the backend folder which handles all fast api calls and supabase setup and databases handling
-- frontend/               # This is the directory which handles all code related to streamlit UI and conversing with the frontend and gcp
-- README.md               # Main README.md 
-- gcp-credentials.json    # GCP credentials file
-- .env file               # env file which has all environment variables and dependencies
-- setup.sh and setup.md   # initial setup files for new users
```

---

## Directory Breakdown

### `/src/`
Contains all logic for:
- Preprocessing resumes and job descriptions
- Feature engineering
- Model training, validation, and evaluation
- Exporting metrics such as accuracy, precision, F1-score to MLflow
- Saving models to Google Artifact Registry

---

### `/data_pipeline/`
This folder includes Airflow DAGs to orchestrate:
- Model **training** - Initial model training with the source data (includes cleaning, pre-processing of raw resume and job description data)
- Model **retraining** using user feedback (re-trains based on 2 factors - push in the github training files, change/mew data in GCP bucket)
- Automated **deployment** of updated models (automatically grabs new resumes pushed into GCP bucket and performs model inference (classification and ranking) and produces a rank for each resume given a job description)

---

### `/backend/`
Contains the **FastAPI backend** that:
- Handles API endpoints for job descriptions, resumes, training_data
- Stores and fetches data from **Supabase**
- Orchestrates interactions between the ML models and the UI

---

### `/frontend/`
This folder contains the **Streamlit app**:
- Interactive UI for uploading job descriptions and resumes
- Shows ranked resumes based on model predictions
- Captures **user feedback** on ranking accuracy
- Displays processed job description and result dashboards

---

## `gcp-credentials.json`
Google Cloud service account key used for:
- Accessing **Google Cloud Storage** for file uploads and model artifacts
- Authenticating from both backend and frontend Docker containers

> Make sure this file is **never committed** to source control.

---

## `.env`
Holds environment variables in the following way:

- Supabase API keys and URLs
- GCS bucket names
- Database connection strings
- API secrets

> This should be stored securely and ignored via `.gitignore`.

---

## CICD Pipeline
The CICD pipeline is set up in google cloud project using Google Cloud Run.
Any push to the `main` branch triggers an automatic build of the frontend and backend and execution. Following a successful build, the application is accessible via a google cloud run app link.

### Cloud Run Services
![image](https://github.com/user-attachments/assets/8d9296ef-bcf2-4d60-bd63-6a8d7826ea9b)


## Step by Step instruction to run the product:

- Run the setup.sh file:

```bash
sh setup.sh
bash setup.sh
```
- If docker is alrady installed, clone the repository directly:

```bash
git clone "https://github.com/ResuMatrix/ResuMatrix.git"
cd ResuMatrix
```

- First, start the backend and the frontend services:

```bash
cd ResuMatrix
docker-compose --env-file .env up --build
```

This command will:

- Start the FastAPI backend (accessible at http://localhost:8000)
- Start the Streamlit frontend (accessible at http://localhost:8501)

- Then we start the docker container to start Airflow to view the deployment and retraining dags:

```bash
cd ResuMatrix
docker-compose up -d
```
Access the Airflow web UI at: http://localhost:8080

## Verify Setup

- Open the frontend: http://localhost:8501
- As a new user, you must provide an email which you have access to. First click on signup, provide email, password and username. 
- You will receive an email from Supabase to authenticate the user. Please verify the email id. 
- Next, login with your username and password. 
- Upload the job description as a txt, pdf or doc file or manually type/pase the job description in the text box.
- After you click on 'Submit Job Description', you can change the fields in the extracted job description using simple promopts in the field provided and then click on 'Regenerate Posting'. 
- Once the extracted job description is satisfied to your needs, you can click on 'Proceed to Resume upload'. 
- The resumes need to be submitted as a .zip file. Once the resumes are extracted, click on 'Submit Resumes'. 
- For the ranking dashboard to appear, it will take a couple of minutes since it's a batch process.  
- Upon completion, you will see a dashboard with the ranked resumes first, followed by the unfit resumes for the job description. 
- These resumes will havea label indicating the rank or will say 'Unfit' otherwise. These resumes are downloadable as well. 
- Post this, the user is directed to a feedback page which could help improve our model and product performance. 
- Completing the feedback or choosing otherwise will eventually log you out of the application. 

- To monitor logs:

```bash
docker compose logs -f
```

- Stopping services

To gracefully stop all services:

```bash
docker compose down
docker stop airflow && docker rm airflow
```

## Alerts & Monitoring
The Airflow DAG triggers email notification on a successful completion or failure of all of the pipelines. This is configured on airflow which monitors for new resume uploads, `src/run_<model>.py` file changes on GitHub.

### Example email alerts
![image](https://github.com/user-attachments/assets/2589a104-b150-4c3a-903d-0d825ca4945b)

Retry Failure
![image](https://github.com/user-attachments/assets/60039c1b-1ca3-4504-96c4-9288f690994b)

### Demo Video

Watch the demo [here](https://drive.google.com/drive/folders/1e-Wpp6Kys9d9bjIS_askIIBXOMCAgQss?usp=drive_link).  

## Contributing

Want to contribute or report issues? Please contact any of the devs.

---

## 📄 License

MIT License

---

## Questions?

For support or queries, contact the project maintainer or open a GitHub issue.
