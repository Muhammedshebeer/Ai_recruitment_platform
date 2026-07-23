import requests

from django.conf import settings

from ..models import JobApplication, JobPost, Profile, Resume


class ChatbotService:

    @staticmethod
    def get_user_context(user):
        context = []

        profile = getattr(user, "profile", None)

        if profile:
            context.append("User role: %s" % profile.role)

        if profile and profile.role == Profile.ROLE_JOB_SEEKER:
            latest_resume = Resume.objects.filter(
                user=user
            ).order_by("-created_at").first()

            if latest_resume:
                context.append("Latest resume title: %s" % latest_resume.title)
                context.append("ATS score: %s" % (latest_resume.ats_score or 0))
                context.append("Target job title: %s" % latest_resume.target_job_title)
                context.append("Resume summary: %s" % latest_resume.summary)
                context.append("Skills: %s" % ", ".join(latest_resume.skills))
                context.append("Missing skills: %s" % ", ".join(latest_resume.missing_skills))
                context.append("Things to add: %s" % ", ".join(latest_resume.things_to_add))

            applications = JobApplication.objects.filter(
                applicant=user
            ).select_related("job").order_by("-created_at")[:5]

            if applications:
                context.append("Recent applications:")
                for application in applications:
                    context.append(
                        "- %s at %s, status: %s, match score: %s"
                        % (
                            application.job.title,
                            application.job.company_name,
                            application.get_status_display(),
                            application.match_score or 0,
                        )
                    )

        elif profile and profile.role == Profile.ROLE_RECRUITER:
            jobs = JobPost.objects.filter(
                recruiter=user
            ).order_by("-created_at")[:5]

            context.append("Recruiter company: %s" % profile.company_name)

            if jobs:
                context.append("Recent recruiter jobs:")
                for job in jobs:
                    context.append(
                        "- %s, status: %s, applications: %s"
                        % (
                            job.title,
                            job.get_status_display(),
                            job.applications.count(),
                        )
                    )

        return "\n".join(context)

    @staticmethod
    def build_messages(user, session, user_message):
        context = ChatbotService.get_user_context(user)

        system_prompt = """
You are an AI assistant inside an AI recruitment platform.

You help job seekers, recruiters, and admins.

Rules:
- Give practical recruitment-related answers.
- If the user is a job seeker, help with resumes, ATS score, job matching, cover letters, and interview preparation.
- If the user is a recruiter, help with job posts, applications, candidate ranking, shortlisting, and hiring process.
- Do not invent fake experience for candidates.
- Keep answers clear, useful, and professional.
- If platform data is not available, say what is missing.

Available user context:
%s
""" % context

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        recent_messages = session.messages.order_by("-created_at")[:10]
        recent_messages = reversed(list(recent_messages))

        for message in recent_messages:
            messages.append(
                {
                    "role": message.role,
                    "content": message.content,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        return messages

    @classmethod
    def ask(cls, user, session, user_message):
        ollama_base_url = getattr(
            settings,
            "OLLAMA_BASE_URL",
            "http://127.0.0.1:11434",
        )

        ollama_model = getattr(
            settings,
            "OLLAMA_MODEL",
            "qwen3",
        )

        url = ollama_base_url.rstrip("/") + "/api/chat"

        payload = {
            "model": ollama_model,
            "messages": cls.build_messages(user, session, user_message),
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 700,
                "num_ctx": 4096,
            },
        }

        response = requests.post(
            url,
            json=payload,
            timeout=300,
        )

        response.raise_for_status()

        result = response.json()

        return result.get("message", {}).get("content", "").strip()