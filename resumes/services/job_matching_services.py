from ..models import JobPost


class JobMatchingService:
    @staticmethod
    def normalize_words(values):
        words = set()

        if not values:
            return words

        for value in values:
            if not value:
                continue

            text = str(value).lower().strip()

            if text:
                words.add(text)

        return words

    @classmethod
    def calculate_match_score(cls, resume, job):
        resume_skills = cls.normalize_words(resume.skills)
        job_skills = cls.normalize_words(job.skills_required)

        if not job_skills:
            return 0

        matched = resume_skills.intersection(job_skills)
        score = int((len(matched) / float(len(job_skills))) * 100)

        if score > 100:
            score = 100

        return score

    @classmethod
    def match_jobs_for_resume(cls, resume, limit=10):
        jobs = JobPost.objects.filter(status=JobPost.STATUS_OPEN).order_by("-created_at")
        matched_jobs = []

        for job in jobs:
            score = cls.calculate_match_score(resume, job)

            if score > 0:
                matched_jobs.append({"job": job, "score": score})

        matched_jobs = sorted(matched_jobs, key=lambda item: item["score"], reverse=True)

        return matched_jobs[:limit]
