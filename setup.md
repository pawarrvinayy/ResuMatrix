ResuMatrix - Project Setup Guide (from Scratch)

This guide helps set up the ResuMatrix project on a new machine using Docker. It includes:

- Installing Docker (Linux-only via `setup.sh`)
- Cloning the project repository
- Starting Airflow
- Running Backend and Frontend services

---

## Prerequisites

- **OS**: Linux (Docker installed via script) / macOS / Windows (Docker Desktop pre-installed)
- **Git installed**
- **Python 3.10 or above**
- **`.env` file** with necessary API keys and credentials
- **Google Cloud JSON Key** (e.g., `gcp-credentials.json`)

---

## 1. Run Setup Script

Run the setup script to install Docker (Linux only), clone the repo, and prep the environment:

```bash
sh setup.sh
```

This will:

- Install Docker if not already installed (Linux only). If on Windows/Mac, will have to pre-install Docker manually. 
- Clone the ResuMatrix repository.

## 2. Navigate to Project Directory

Move into the cloned project directory:

```bash
cd ResuMatrix
```

The project structure should look like this:

ResuMatrix/
│
├── .dvc
├── backend/
├── data_pipeline/
├── frontend/
├── logs/
├── mlruns/
├── .env
├── gcp-credentials.json
├── docker-compose.yaml
├── README.md
├── setup.sh
├── setup.md

## 3. Start Airflow (First Docker Container)

The below command starts the  docker container for the deployment and retraining pipeline to run:

```bash
cd ResuMatrix
docker-compose up -d
```
Access the Airflow web UI at: http://localhost:8080

## 4. Start Backend and Frontend Services

```bash
cd ResuMatrix
docker-compose --env-file .env up --build
```

This command will:

- Start the FastAPI backend (accessible at http://localhost:8000)
- Start the Streamlit frontend (accessible at http://localhost:8501)

## 5. Verify Setup

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

## 6. Stopping services

To gracefully stop all services:

```bash
docker compose down
docker stop airflow && docker rm airflow
```

## Notes

The .env file must include:

- Supabase project URL and API key
- GCP bucket name
- Any other secrets or environment variables
- Backend uses GOOGLE_APPLICATION_CREDENTIALS to connect to GCP
- All containers run isolated but communicate via Docker network