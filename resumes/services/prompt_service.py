class PromptService:
    @staticmethod
    def resume_analysis_prompt(
        resume_text,
        target_job_title="",
        target_job_description="",
        target_experience_level="",
        target_location="",
    ):
        resume_text = resume_text[:7000]
        target_job_description = target_job_description[:5000]

        return """
You are an expert ATS resume analyzer and recruitment consultant.

Analyze the resume against the target job.

Target Job Title:
%s

Target Experience Level:
%s

Target Location:
%s

Target Job Description:
%s

Resume Text:
%s

Return ONLY valid JSON.
Do not use markdown.
Do not explain outside JSON.
Do not include <think> tags.

Return exactly this JSON structure:

{
    "ats_score": 0,
    "job_match_score": 0,
    "summary": "",
    "improved_summary": "",
    "skills": [],
    "missing_skills": [],
    "strengths": [],
    "weak_sections": [],
    "improvements": [],
    "things_to_add": [],
    "resume_bullet_points": [],
    "keywords_to_add": [],
    "job_match_feedback": ""
}

Rules:
- ats_score must be a number between 0 and 100.
- job_match_score must be a number between 0 and 100 based on resume fit to the target job.
- Compare the resume with the target job description.
- skills must include skills already found in the resume.
- missing_skills must include skills required by the job but missing from the resume.
- weak_sections must identify weak parts such as summary, skills, experience, projects, certifications, or achievements.
- things_to_add must explain what the candidate should add to increase ATS score.
- resume_bullet_points must be ready-to-copy bullet points the candidate can add to the resume.
- keywords_to_add must include ATS keywords from the job description.
- improved_summary must be a stronger professional summary for the target job.
- improvements must be practical suggestions.
- job_match_feedback must be a short paragraph explaining how well the resume matches the target job.
- Do not invent fake experience.
- If experience is missing, say to add it only if the candidate genuinely has that experience.
- Maximum 12 skills.
- Maximum 10 missing_skills.
- Maximum 8 things_to_add.
- Maximum 8 resume_bullet_points.
- Maximum 12 keywords_to_add.
""" % (
            target_job_title,
            target_experience_level,
            target_location,
            target_job_description,
            resume_text,
        )
