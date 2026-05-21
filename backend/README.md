# ResuMatrix Backend

This directory hosts a dockerized project for the backend that runs on the FastAPI runtime using uvicorn.

To run this project, you'll need Docker or you can alternatively run it with `uvicorn` and the `uv` python package manager.
#### Please refer to the root directory for set up instructions

### Directory Structure

```
/                                # Backend Root   
-- app/                          # FastAPI App directory
    -- api/                      # Api directory holds the exposed endpoints
        -- routes/               # Routes for data API: jobs, resumes, training tables in supabase
        -- deps.py               # Dependency injection of all services
        -- main.py               # API router main file
    -- core/                     # Config and other settings 
    -- services/                 # Services and business logic
        -- database.py           # Database operations
        -- google_genai.py       # Gemini client and Google Models API
        -- models.py             # Gemini structured output Pydantic models
        -- pinecone.py           # Pinecone client for upserting section wise embeddings
        -- prompts.py            # Structured ouput prompts
        -- ranking.py            # Ranking algorithm with Borda ranker
        -- storage.py            # GCP bucket client
        -- utils.py              # Utilities, retry mechanism for Gemini client
    -- main.py                   # Application entrypoint
    -- models.py                 # Database pydantic models

```

### Backend tasks

- Uploads resumes, create jobs
- Communicates with the Supabase Database
- Extracts sections from Resume
- Communicates with the Gemini client
- Converts resume sections to Gemini embeddings
- Upserts embeddings to Pinecone for a section-wise view for similarity search
- Hosts Borda ranker

### Ranking Flow
- Structured Output: The backend structures raw resume text and ranks candidates based on multiple sections.
- LLM (Gemini models): Used to extract structured sections from raw resumes
- Schema Validation: Pydantic with exponential retry mechanism Validates and formats extracted sections
- Resume Sections: Education, Work Experience, Personal Projects, Others
- Embeddings: Generated per section and stored in Pinecone under separate namespaces
- Ranking: Top 100 resumes fetched per section and ranked using the Borda count algorithm
- Final Output: Unified ranking across all sections for each candidate
