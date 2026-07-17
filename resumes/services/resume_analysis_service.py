from .ai_service import AIService
from .pdf_service import PDFService
from .prompt_service import PromptService


class ResumeAnalysisService:
    @staticmethod
    def normalize_list(value):
        if isinstance(value, list):
            return value

        if isinstance(value, str) and value.strip():
            return [value.strip()]

        return []

    @staticmethod
    def normalize_score(value):
        try:
            score = int(value)
        except:
            score = 0

        if score < 0:
            score = 0

        if score > 100:
            score = 100

        return score

    @classmethod
    def analyze(cls, resume):
        text = PDFService.extract_text(resume.pdf.path)
        resume.extracted_text = text

        prompt = PromptService.resume_analysis_prompt(
            resume_text=text,
            target_job_title=resume.target_job_title,
            target_job_description=resume.target_job_description,
            target_experience_level=resume.target_experience_level,
            target_location=resume.target_location,
        )

        analysis = AIService.ask(prompt)

        if not isinstance(analysis, dict):
            raise ValueError("AI response must be a JSON object.")

        ats_score = cls.normalize_score(analysis.get("ats_score", 0))
        job_match_score = cls.normalize_score(analysis.get("job_match_score", 0))

        cleaned_analysis = {
            "ats_score": ats_score,
            "job_match_score": job_match_score,
            "summary": analysis.get("summary", ""),
            "improved_summary": analysis.get("improved_summary", ""),
            "skills": cls.normalize_list(analysis.get("skills", [])),
            "missing_skills": cls.normalize_list(analysis.get("missing_skills", [])),
            "strengths": cls.normalize_list(analysis.get("strengths", [])),
            "weak_sections": cls.normalize_list(analysis.get("weak_sections", [])),
            "improvements": cls.normalize_list(analysis.get("improvements", [])),
            "things_to_add": cls.normalize_list(analysis.get("things_to_add", [])),
            "resume_bullet_points": cls.normalize_list(analysis.get("resume_bullet_points", [])),
            "keywords_to_add": cls.normalize_list(analysis.get("keywords_to_add", [])),
            "job_match_feedback": analysis.get("job_match_feedback", ""),
        }

        resume.ai_response = cleaned_analysis
        resume.ats_score = ats_score
        resume.summary = cleaned_analysis["summary"]
        resume.save()

        return resume
