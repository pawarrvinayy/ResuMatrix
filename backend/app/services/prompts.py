
class ResumePromptTemplates:
    """Class to manage prompt templates for resume processing."""
    
    @staticmethod
    def get_resume_prompt_template():
        """Return the standard resume extraction prompt template."""
        return """Given the resume text below, extract and return a structured JSON object.

# CRITICAL INSTRUCTIONS
- DO NOT add any information not explicitly stated in the resume
- Do not hallucinate or invent details, skills, dates, or responsibilities
- If information is missing, use "" for strings or [] for arrays — never null
- DO NOT include time in datetime outputs; format dates as YYYY-MM-DD
- Convert all gendered pronouns to gender-neutral alternatives (they/them)

# Output Schema — you MUST return JSON matching this exact structure:
{
  "basics": {
    "name": "",
    "email": "",
    "phone": "",
    "website": "",
    "summary": "3-sentence summary of the candidate highlighting key strengths",
    "location": {
      "address": "",
      "postalCode": "",
      "city": "",
      "countryCode": ""
    },
    "github": "",
    "linkedin": "",
    "twitter": "",
    "languages": [
      {"language": "English", "fluency": "Native speaker"}
    ]
  },
  "workexp": [
    {
      "companyName": "Acme Corp",
      "position": "Software Engineer",
      "startDate": "2021-06-01",
      "endDate": "2023-08-31",
      "summary": ["Responsibility or achievement as a bullet string", "Another bullet"],
      "skills": ["Python", "PostgreSQL", "Docker"]
    }
  ],
  "education": [
    "Master of Science in Computer Science, MIT, 2020-09-01 to 2022-05-31, GPA 3.9"
  ],
  "personal_projects": [
    {
      "projectName": "My ML Project",
      "startDate": "2022-01-01",
      "endDate": "2022-05-01",
      "highlights": ["Built a classifier with 94% accuracy", "Deployed on AWS Lambda"],
      "projectUrl": "",
      "keywords": ["Python", "scikit-learn", "AWS"]
    }
  ],
  "skills": ["Python", "SQL", "Machine Learning"],
  "awards": [
    {
      "title": "Dean's List",
      "dateReceived": "2021-05-01",
      "awarder": "Boston University",
      "summary": ""
    }
  ],
  "certificates": [
    {
      "certificateName": "AWS Certified Solutions Architect",
      "dateIssued": "2022-03-01",
      "issuer": "Amazon Web Services",
      "certificateUrl": ""
    }
  ],
  "publications": [
    {
      "publicationName": "Deep Learning for NLP",
      "publisherName": "NeurIPS",
      "releaseDate": "2023-12-01",
      "publicationUrl": "",
      "summary": ""
    }
  ]
}

# Field Rules

## basics
- summary: 3 sentences max, highlight key skills and experience level
- github/linkedin: full URLs if found; "" if not present
- languages: only include non-English languages plus English if explicitly stated; omit if none mentioned
- location: fill only what is explicitly stated; use "" for unknown subfields

## education
- MUST be a flat list of strings — one string per degree
- Format: "Degree Name, Institution, start-date to end-date[, GPA if stated][, additional notes]"
- Example: "Bachelor of Engineering in Computer Science, Boston University, 2017-04-01 to 2021-04-01, GPA 3.4/4.0, Dean's List"
- Do NOT return education as objects — strings only

## workexp
- Only include actual employment (not academic projects or internships at universities)
- companyName and position are required; use "" if truly unreadable
- summary: list of bullet strings describing responsibilities/achievements
- skills: max 7 most relevant technical skills per position

## personal_projects
- Academic projects, side projects, course projects all go here — never in workexp
- projectName is required; use "" only if completely unreadable
- highlights: bullet strings describing what was built or achieved
- keywords: technologies and tools used

## skills
- Global skills list from the dedicated skills section of the resume
- Exclude natural spoken languages (English, French, etc.)
- Include writing, literature review, and similar professional skills

## awards
- Only actual awards/honours (Dean's List, scholarships, competition wins)
- Do NOT include work experience entries as awards

# Resume text:
"""


