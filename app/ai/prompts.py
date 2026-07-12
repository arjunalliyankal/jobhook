RESUME_PARSE_PROMPT = """
You are a resume parser. Extract every single detail from the resume text below with maximum precision.
Return ONLY a valid JSON object with these exact keys:
{{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "linkedin": "",
  "portfolio": "",
  "summary": "Detailed professional summary or objective statement.",
  "skills": ["List every technical and soft skill found"],
  "experience": [{{"company": "", "title": "", "location": "", "start": "", "end": "", "bullets": ["Every single bullet point and description for this role"]}}],
  "education": [{{"school": "", "degree": "", "field": "", "year": "", "location": ""}}],
  "projects": [{{"name": "", "description": "Full detailed description of the project and your role", "link": "", "technologies": []}}],
  "certificates": [{{"name": "", "issuer": "", "date": ""}}],
  "courses": [{{"name": "", "platform": "", "date": ""}}],
  "languages": ["List all languages mentioned"],
  "interests": ["List all interests or hobbies mentioned"]
}}

Resume Text:
{resume_text}
"""

RESUME_SUGGESTIONS_PROMPT = """
You are an expert resume consultant and ATS optimization specialist.

The candidate's resume scored {score}% against the job description below.
Missing keywords: {missing_keywords}

Your task:
1. List 5 specific, actionable bullet-point improvements to the resume
2. Suggest how to naturally incorporate the missing keywords
3. Identify any weak language and suggest stronger alternatives
4. Rewrite the candidate's professional summary to naturally embed the missing keywords
5. Rewrite the candidate's experience bullet points to be stronger and include the missing keywords. IMPORTANT: Keep the exact same companies and titles as the original experience array provided.

Job Description:
{jd_text}

Resume Text:
{resume_text}

Original Experience Array (refer to this for rewriting):
{parsed_experience}

Return a structured JSON:
{{
  "improvements": [],
  "keyword_suggestions": [],
  "language_upgrades": [],
  "revised_summary": "",
  "revised_experience": [{{"company": "", "title": "", "location": "", "start": "", "end": "", "bullets": []}}]
}}
"""

COVER_LETTER_PROMPT = """
You are a professional cover letter writer. Write a compelling, personalized
cover letter for the following applicant targeting the role described below.

Guidelines:
- 3–4 paragraphs, professional but personable
- Opening: Strong hook referencing the specific role and company
- Body: Connect candidate's top 3 achievements to the role requirements
- Closing: Confident call-to-action
- Do NOT use generic filler phrases like "I am writing to apply for..."

Applicant Info:
Name: {name}
Target Role: {role}
Company: {company}
Top Skills: {skills}
Key Achievements: {achievements}

Job Description:
{jd_text}

Return ONLY the cover letter text, no additional commentary.
"""

SKILL_GAP_ADVICE_PROMPT = """
The candidate wants to become a {target_role}.
They have these skills: {current_skills}
They are missing these required skills: {missing_skills}

Provide a concise learning roadmap:
1. Rank the missing skills by importance for the target role
2. For each top 3 skill, suggest one free resource to learn it
3. Estimate weeks to reach job-ready proficiency

Return as JSON:
{{
  "prioritized_skills": [],
  "learning_resources": {{}},
  "timeline_weeks": {{}}
}}
"""
