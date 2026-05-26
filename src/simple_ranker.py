import os
import sys
import json
import re
import requests
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_API_KEY = os.environ["SUPABASE_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
RESUMATRIX_API_URL = os.environ.get("RESUMATRIX_API_URL", "http://localhost:8000")

MODEL = "gpt-4o-mini"
FIT_THRESHOLD = 40  # overall score out of 100

WEIGHTS = {
    "skills": 0.40,
    "experience": 0.30,
    "education": 0.15,
    "projects": 0.15,
}

if len(sys.argv) < 2:
    print("Usage: python simple_ranker.py <job_id>")
    sys.exit(1)

job_id = sys.argv[1]
print(f"Starting LLM ranker for job_id: {job_id}")

supabase = create_client(SUPABASE_URL, SUPABASE_API_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)


# ── LLM helpers ───────────────────────────────────────────────────────────────

def chat(system: str, user: str, temperature: float = 0.0) -> str:
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content


def parse_json(raw: str, fallback: dict) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        print(f"  [WARN] JSON parse failed, using fallback. Raw: {raw[:120]}")
        return fallback


# ── STEP 1: Extract structured requirements from JD ──────────────────────────

def extract_jd_requirements(jd_text: str) -> dict:
    system = (
        "You are a precise job-description parser. "
        "Return ONLY valid JSON matching the schema exactly — no extra keys, no prose."
    )
    user = f"""Extract structured requirements from this job description.

Return JSON with exactly these keys:
{{
  "required_skills": ["list of hard required technical skills"],
  "preferred_skills": ["list of nice-to-have skills"],
  "min_years_experience": <integer, 0 if not stated>,
  "education_required": "<degree level required, e.g. Bachelor's, Master's, or None>",
  "key_responsibilities": ["list of 5-8 core duties/responsibilities"]
}}

Job Description:
{jd_text}"""

    fallback = {
        "required_skills": [],
        "preferred_skills": [],
        "min_years_experience": 0,
        "education_required": "None",
        "key_responsibilities": [],
    }
    raw = chat(system, user)
    result = parse_json(raw, fallback)
    # Coerce types
    result["min_years_experience"] = int(result.get("min_years_experience") or 0)
    result["required_skills"] = result.get("required_skills") or []
    result["preferred_skills"] = result.get("preferred_skills") or []
    result["key_responsibilities"] = result.get("key_responsibilities") or []
    result["education_required"] = result.get("education_required") or "None"
    return result


# ── STEP 2a: Strip PII from resume text ──────────────────────────────────────

def strip_pii(resume_text: str) -> str:
    system = (
        "You are a privacy filter. Remove all personally identifiable information "
        "from the resume text: full names, email addresses, phone numbers, physical "
        "addresses, LinkedIn URLs, GitHub URLs, personal websites, and any other "
        "direct identifiers. Replace each removed item with the token [REDACTED]. "
        "Return ONLY the sanitised text — no JSON, no commentary."
    )
    # Call without json_object format since we want plain text
    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": resume_text},
        ],
    )
    return resp.choices[0].message.content


# ── STEP 2b: Extract structured profile from sanitised resume ─────────────────

def extract_resume_profile(sanitised_text: str) -> dict:
    system = (
        "You are a precise resume parser. "
        "Return ONLY valid JSON matching the schema exactly — no extra keys, no prose."
    )
    user = f"""Extract a structured profile from this resume.

Return JSON with exactly these keys:
{{
  "skills": ["list of all technical and professional skills mentioned"],
  "years_experience": <integer total years of professional work experience, 0 if student/none>,
  "education": "<highest degree earned, e.g. Bachelor's in Computer Science, Master's in Data Science, PhD, or None>",
  "recent_titles": ["list of up to 3 most recent job titles held"],
  "projects": ["list of up to 5 notable projects or achievements described"]
}}

Resume:
{sanitised_text}"""

    fallback = {
        "skills": [],
        "years_experience": 0,
        "education": "None",
        "recent_titles": [],
        "projects": [],
    }
    raw = chat(system, user)
    result = parse_json(raw, fallback)
    result["years_experience"] = int(result.get("years_experience") or 0)
    result["skills"] = result.get("skills") or []
    result["recent_titles"] = result.get("recent_titles") or []
    result["projects"] = result.get("projects") or []
    result["education"] = result.get("education") or "None"
    return result


# ── STEP 3: Intelligent single-call scorer ────────────────────────────────────

def intelligent_scorer(jd: dict, profile: dict) -> dict:
    """Single GPT-4o-mini call returning scores, per-section reasoning,
    a recruiter summary, and missing keywords."""
    system = (
        "You are a senior engineering recruiter with 10 years of experience screening "
        "technical candidates. Analyze candidate fit carefully and honestly. Consider "
        "transferable skills, not just exact keyword matches. Consider depth and recency "
        "of experience. Be critical — most candidates are not perfect fits. "
        "Return ONLY valid JSON, no other text."
    )
    user = f"""Score this candidate against the job requirements.

JD Requirements:
- Required skills: {jd["required_skills"]}
- Preferred skills: {jd["preferred_skills"]}
- Min experience: {jd["min_years_experience"]} years
- Education: {jd["education_required"]}
- Key responsibilities: {jd["key_responsibilities"]}

Candidate Profile:
- Skills: {profile["skills"]}
- Years experience: {profile["years_experience"]}
- Education: {profile["education"]}
- Recent titles: {profile["recent_titles"]}
- Projects: {profile["projects"]}

Return this exact JSON:
{{
  "reasoning": {{
    "skills": "2-3 sentences analyzing skill match and gaps honestly",
    "experience": "2-3 sentences on experience relevance and depth",
    "education": "1 sentence on education fit",
    "projects": "2-3 sentences on whether projects show real applied experience"
  }},
  "scores": {{
    "skills": <integer 0-100>,
    "experience": <integer 0-100>,
    "education": <integer 0-100>,
    "projects": <integer 0-100>
  }},
  "summary": "One honest recruiter verdict sentence",
  "missing_keywords": ["list only specific skills, technologies, or tools mentioned in the JD that are absent from the resume — short keywords only like 'Airflow', 'LangChain', 'Docker', 'RAG' — NOT full sentences, NOT responsibilities"]
}}"""

    fallback = {
        "reasoning": {
            "skills": "Unable to assess.",
            "experience": "Unable to assess.",
            "education": "Unable to assess.",
            "projects": "Unable to assess.",
        },
        "scores": {"skills": 50, "experience": 50, "education": 50, "projects": 50},
        "summary": "Assessment unavailable.",
        "missing_keywords": [],
    }
    raw = chat(system, user, temperature=0)
    result = parse_json(raw, fallback)

    scores_raw = result.get("scores") or {}
    scores = {
        "skills":     float(scores_raw.get("skills",     50)),
        "experience": float(scores_raw.get("experience", 50)),
        "education":  float(scores_raw.get("education",  50)),
        "projects":   float(scores_raw.get("projects",   50)),
    }
    scores["overall"] = round(
        scores["skills"]     * WEIGHTS["skills"]
        + scores["experience"] * WEIGHTS["experience"]
        + scores["education"]  * WEIGHTS["education"]
        + scores["projects"]   * WEIGHTS["projects"],
        1,
    )

    return {
        "scores": scores,
        "reasoning": result.get("reasoning") or fallback["reasoning"],
        "summary": result.get("summary") or fallback["summary"],
        "missing_keywords": result.get("missing_keywords") or [],
    }


# ── MAIN ──────────────────────────────────────────────────────────────────────

# 1. Fetch job description
print("Fetching job description...")
job_result = supabase.table("jobs").select("job_text").eq("id", job_id).execute()
if not job_result.data:
    print(f"No job found with id: {job_id}")
    sys.exit(1)
jd_text = job_result.data[0]["job_text"]
print(f"  JD loaded ({len(jd_text)} chars)")

# 2. Fetch resumes
print("Fetching resumes...")
resumes_result = (
    supabase.table("resumes")
    .select("id, resume_text")
    .eq("job_id", job_id)
    .execute()
)
resumes = resumes_result.data
if not resumes:
    print(f"No resumes found for job_id: {job_id}")
    sys.exit(1)
print(f"  Found {len(resumes)} resumes")

# 3. Extract JD requirements once
print("Extracting JD requirements with gpt-4o-mini...")
jd_req = extract_jd_requirements(jd_text)
print(f"  Required skills ({len(jd_req['required_skills'])}): {jd_req['required_skills'][:5]}")
print(f"  Min experience: {jd_req['min_years_experience']} years")
print(f"  Education: {jd_req['education_required']}")

# 4. Process each resume
print("Processing resumes...")
scored = []
for i, resume in enumerate(resumes):
    print(f"\n  [{i+1}/{len(resumes)}] resume {resume['id']}")

    # 4a. Strip PII
    print("    Stripping PII...")
    sanitised = strip_pii(resume["resume_text"])

    # 4b. Extract structured profile
    print("    Extracting profile...")
    profile = extract_resume_profile(sanitised)
    print(f"    Skills: {profile['skills'][:4]}, Exp: {profile['years_experience']}y, "
          f"Edu: {profile['education']}")

    # 4c. Score with single intelligent LLM call
    print("    Scoring...")
    result = intelligent_scorer(jd_req, profile)
    scores = result["scores"]
    print(f"    Scores → skills:{scores['skills']} exp:{scores['experience']} "
          f"edu:{scores['education']} proj:{scores['projects']} "
          f"overall:{scores['overall']}")
    print(f"    Summary: {result['summary']}")
    print(f"    Missing: {result['missing_keywords']}")

    scored.append({
        "id": resume["id"],
        "scores": scores,
        "reasoning": result["reasoning"],
        "summary": result["summary"],
        "missing_keywords": result["missing_keywords"],
        "fit": scores["overall"] >= FIT_THRESHOLD,
    })

# 5. Sort fit resumes by overall score descending, assign rank positions
fit_resumes = sorted(
    [r for r in scored if r["fit"]],
    key=lambda x: x["scores"]["overall"],
    reverse=True,
)
unfit_resumes = [r for r in scored if not r["fit"]]
print(f"\nResults: {len(fit_resumes)} fit, {len(unfit_resumes)} unfit")

# 6. Write to Supabase
print("Updating Supabase...")
for rank, resume in enumerate(fit_resumes, start=1):
    s = resume["scores"]
    section_scores = {
        "skills": s["skills"],
        "experience": s["experience"],
        "education": s["education"],
        "projects": s["projects"],
    }
    supabase.table("resumes").update({
        "fit_probability": round(s["overall"] / 100, 4),
        "status": rank,
        "section_scores": json.dumps(section_scores),
        "reasoning": json.dumps(resume["reasoning"]),
        "summary": resume["summary"],
        "missing_keywords": json.dumps(resume["missing_keywords"]),
    }).eq("id", resume["id"]).execute()
    print(f"  #{rank} {resume['id']} — {s['overall']}%")

for resume in unfit_resumes:
    s = resume["scores"]
    section_scores = {
        "skills": s["skills"],
        "experience": s["experience"],
        "education": s["education"],
        "projects": s["projects"],
    }
    supabase.table("resumes").update({
        "fit_probability": round(s["overall"] / 100, 4),
        "status": -1,
        "section_scores": json.dumps(section_scores),
        "reasoning": json.dumps(resume["reasoning"]),
        "summary": resume["summary"],
        "missing_keywords": json.dumps(resume["missing_keywords"]),
    }).eq("id", resume["id"]).execute()
    print(f"  UNFIT {resume['id']} — {s['overall']}%")

# 7. Mark job complete
print("Marking job complete...")
supabase.table("jobs").update({"status": 1}).eq("id", job_id).execute()

# 8. Trigger Gemini pipeline (silently ignored if billing unavailable)
print(f"Triggering /rank endpoint...")
try:
    response = requests.post(f"{RESUMATRIX_API_URL}/api/jobs/{job_id}/rank", timeout=10)
    if response.ok:
        print("  /rank triggered successfully")
    else:
        print(f"  /rank skipped: {response.status_code}")
except requests.RequestException as e:
    print(f"  /rank unreachable: {e}")

print("\nDone.")
