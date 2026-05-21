import os
import sys
import requests
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_API_KEY = os.environ["SUPABASE_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
RESUMATRIX_API_URL = os.environ.get("RESUMATRIX_API_URL", "http://localhost:8000")
FIT_THRESHOLD = 0.15
EMBED_MODEL = "text-embedding-3-small"

if len(sys.argv) < 2:
    print("Usage: python simple_ranker.py <job_id>")
    sys.exit(1)

job_id = sys.argv[1]
print(f"Starting ranker for job_id: {job_id}")

supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)


def get_embedding(text):
    response = openai_client.embeddings.create(input=text, model=EMBED_MODEL)
    return np.array(response.data[0].embedding)


def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# 1. Fetch job description
print("Fetching job description...")
job_result = supabase.table("jobs").select("job_text").eq("id", job_id).execute()
if not job_result.data:
    print(f"No job found with id: {job_id}")
    sys.exit(1)
jd_text = job_result.data[0]["job_text"]
print(f"Job description loaded ({len(jd_text)} chars)")

# 2. Fetch resumes
print("Fetching resumes...")
resumes_result = supabase.table("resumes").select("id, resume_text").eq("job_id", job_id).execute()
resumes = resumes_result.data
if not resumes:
    print(f"No resumes found for job_id: {job_id}")
    sys.exit(1)
print(f"Found {len(resumes)} resumes")

# 3. Embed JD
print("Embedding job description...")
jd_embedding = get_embedding(jd_text)

# 4. Embed resumes and compute similarity
print("Embedding resumes and computing similarity scores...")
updates = []
for i, resume in enumerate(resumes):
    resume_embedding = get_embedding(resume["resume_text"])
    score = cosine_similarity(resume_embedding, jd_embedding)
    status = 1 if score > FIT_THRESHOLD else -1
    updates.append({"id": resume["id"], "fit_probability": score, "status": status})
    print(f"  [{i+1}/{len(resumes)}] resume {resume['id']} — score: {score:.4f} → {'FIT' if status == 1 else 'UNFIT'}")

# 5. Update Supabase
print("Updating Supabase...")
for update in updates:
    supabase.table("resumes").update({
        "fit_probability": update["fit_probability"],
        "status": update["status"]
    }).eq("id", update["id"]).execute()
print(f"Updated {len(updates)} resumes")

# 6. Mark job as complete in Supabase (status=1 signals frontend polling to stop)
print("Updating job status to 1 (complete)...")
supabase.table("jobs").update({"status": 1}).eq("id", job_id).execute()
print("Job status updated")

# 7. Trigger ranking
print(f"Triggering ranking at {RESUMATRIX_API_URL}/api/jobs/{job_id}/rank ...")
response = requests.post(f"{RESUMATRIX_API_URL}/api/jobs/{job_id}/rank")
if response.ok:
    print("Ranking triggered successfully")
else:
    print(f"Ranking request failed: {response.status_code} {response.text}")

print("Done.")
