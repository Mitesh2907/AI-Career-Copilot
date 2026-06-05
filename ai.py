from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

def analyze_resume(resume_text, user_goal):

    prompt = f"""
User Goal: {user_goal}

Resume:
{resume_text}

You are an expert ATS system, hiring manager, and career coach.

Return ONLY valid JSON in this exact format:

{{
    "resume_score": 0,
    "ats_score": 0,
    "strengths": [],
    "weaknesses": [],
    "skills": [],
    "missing_skills": [],
    "roadmap": [],
    "interview_questions": []
}}

Rules:
- resume_score must be between 0 and 100.
- ats_score must be between 0 and 100.
- Evaluate based on skills, projects, resume quality, technologies, and relevance to the target role.
- strengths should contain 3 to 5 strong points.
- weaknesses should contain 3 to 5 improvement areas.
- skills should contain relevant skills found in the resume.
- missing_skills should contain important missing skills for the target role.
- roadmap should contain 5 to 10 learning steps.
- interview_questions should contain at least 10 interview questions.
- Return JSON only. No explanation. No markdown.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict ATS resume evaluator and hiring manager."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content

        start = content.find("{")
        end = content.rfind("}") + 1

        json_text = content[start:end]

        return json.loads(json_text)

    except Exception as e:
        return {
            "resume_score": 0,
            "ats_score": 0,
            "strengths": [],
            "weaknesses": [],
            "skills": [],
            "missing_skills": [],
            "roadmap": [],
            "interview_questions": [],
            "error": str(e)
        }