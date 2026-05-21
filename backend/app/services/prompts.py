
class ResumePromptTemplates:
    """Class to manage prompt templates for resume processing."""
    
    @staticmethod
    def get_resume_prompt_template():
        """Return the standard resume extraction prompt template."""
        return """Given the resume text, create a structured JSON representation following these guidelines:

# CRITICAL INSTRUCTION
- DO NOT add any information that is not explicitly stated in the original resume
- Do not hallucinate or invent details, skills, dates, or responsibilities
- If information is missing or unclear, leave the corresponding field empty rather than guessing
- Only include verifiable information from the provided text
- DO NOT INCLUE TIME IN DATETIME OUTPUTS

- Use exactly 2 spaces for indentation
- NEVER use tab characters (\\t)
- Avoid line breaks within field values

# Education
- Format the education segment in 1-2 lines for each degree/endeavor. Write a complete conversational sentence.
  An example is - The candidate pursued a Bachelor of Engineering at Boston University from 01/04/2017 to 01/04/2021 and has secured a GPA of 3.4 out of 4. The candidate made it to the dean's list.
  Another example - The candidate is currently a graduate student majoring in Data Science at Northeastern University. They started their course on 01/09/2023 and are expected to complete it by 12/01/2025. 

  They have a grade of 9.5 out of 10 and have studied subjects like Machine Learning, Natural Language Processing and Computer Vision. 

# Work Experience Extraction

- Clearly distinguish between actual employment and educational projects
- For each position capture: company, title, dates, responsibilities, and key skills
- If multiple positions exist at the same company, represent them as separate experiences
- Include all work experiences mentioned in the resume.
- Extract date information carefully - if dates appear as "01/1to01/1" pattern, try to infer actual dates from context

# Skills Extraction Rules
- For each position, identify maximum 7 most relevant technical and conceptual skills
- Include both technical skills (languages, tools, frameworks) and broader competencies (testing methodologies, domain knowledge)
- When similar technologies appear (like PostgreSQL, MySQL, PL/SQL), select only the most representative one
- Prioritize skills that directly relate to the described responsibilities
- If the resume has a section for skills, add all of them into the skills section.

# Formatting Guidelines
- Convert any gendered pronouns to gender-neutral alternatives
- Format dates in YYYY-MM-DD format when possible

- For education entries with single dates, assume it's the graduation date
- Match any provided links to appropriate fields (LinkedIn, GitHub, personal website)
- Include achievements in the awards section
- Add any github, linkedin and personal website links found in the resume.
- If a link pointing to a domain github.com but is not a repository, it is their github link.
- Add a simple summary section summarizing the entire candidate profile in 3 sentences. Highlight key parts of their resume in these sentences.

- Include any research paper publications in the publications section.
- Do not include natural languages like english, french in the skills section. Writing, literature review and similar language skills should be included.


# Critical Classification Rules
  - **Academic projects** must ONLY go in personal_projects section, never in work experience
  - Identify academic projects by presence of:
      - University/school names in organization field
      - Course names (e.g., "Advanced Web Application Development")
      - Semester/year indicators (Fall 2012, Spring 2012)
  - Awards are only classified as such if is an award for performance or something similar. Work experience is not an award.


# Work Experience Requirements

  Only include positions that:
  - Have explicit employment indicators: "Software Engineer", "Employed at", "Worked at"
  - Show duration patterns matching employment (not academic semesters)
"""


