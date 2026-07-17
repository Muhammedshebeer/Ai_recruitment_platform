from .ai_service import AIService


class CareerToolsService:
    @staticmethod
    def normalize_list(value):
        if isinstance(value, list):
            return value

        if isinstance(value, str) and value.strip():
            return [value.strip()]

        return []

    @classmethod
    def generate_cover_letter(cls, resume, job):
        resume_text = (resume.extracted_text or "")[:6000]

        prompt = """
You are a professional career coach and cover letter writer.

Create a tailored cover letter for this job using only information supported by the resume.
Do not invent fake experience.
Keep it concise, confident, and professional.

Job Title:
%s

Company:
%s

Location:
%s

Job Description:
%s

Requirements:
%s

Candidate Resume:
%s

Return ONLY valid JSON in this exact structure:

{
    "cover_letter": ""
}

Rules:
- cover_letter must be ready to copy.
- Mention the company and role.
- Keep it between 250 and 400 words.
- Do not use markdown.
""" % (
            job.title,
            job.company_name,
            job.location,
            job.description,
            job.requirements,
            resume_text,
        )

        response = AIService.ask(prompt)

        if not isinstance(response, dict):
            return ""

        return response.get("cover_letter", "")

    @classmethod
    def generate_interview_questions(cls, resume, job):
        resume_text = (resume.extracted_text or "")[:6000]

        prompt = """
You are a senior recruiter and technical interviewer.

Generate interview preparation questions for this candidate based on the job and resume.

Job Title:
%s

Company:
%s

Job Description:
%s

Requirements:
%s

Candidate Resume:
%s

Return ONLY valid JSON in this exact structure:

{
    "technical_questions": [],
    "hr_questions": [],
    "suggested_answers": [],
    "preparation_tips": []
}

Rules:
- technical_questions: role-specific technical questions.
- hr_questions: behavioral and general interview questions.
- suggested_answers: short model answers or answer frameworks.
- preparation_tips: practical preparation advice.
- Do not use markdown.
- Maximum 10 technical_questions.
- Maximum 8 hr_questions.
- Maximum 8 suggested_answers.
- Maximum 8 preparation_tips.
""" % (
            job.title,
            job.company_name,
            job.description,
            job.requirements,
            resume_text,
        )

        response = AIService.ask(prompt)

        if not isinstance(response, dict):
            response = {}

        return {
            "technical_questions": cls.normalize_list(response.get("technical_questions", [])),
            "hr_questions": cls.normalize_list(response.get("hr_questions", [])),
            "suggested_answers": cls.normalize_list(response.get("suggested_answers", [])),
            "preparation_tips": cls.normalize_list(response.get("preparation_tips", [])),
        }
