import requests

from django.conf import settings

from ..models import JobApplication, JobPost, Profile, Resume
from .ai_service import AIService


class ChatbotService:

    @staticmethod
    def safe_join(values):
        if not values:
            return ""

        return ", ".join([str(value) for value in values if value])

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
                context.append("Target job title: %s" % getattr(latest_resume, "target_job_title", ""))
                context.append("Resume summary: %s" % (latest_resume.summary or ""))
                context.append("Skills: %s" % ChatbotService.safe_join(latest_resume.skills))
                context.append("Missing skills: %s" % ChatbotService.safe_join(latest_resume.missing_skills))
                context.append("Things to add: %s" % ChatbotService.safe_join(latest_resume.things_to_add))

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

            context.append("Recruiter company: %s" % (profile.company_name or ""))

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

        elif user.is_staff:
            context.append("User role: platform admin")

        return "\n".join(context)

    @staticmethod
    def normalize_role(role):
        """
        Your database should store chatbot messages as:
        user / assistant

        If any old messages use agent/tool/system, normalize them
        so OpenAI receives valid chat roles.
        """

        if role == "user":
            return "user"

        if role in ["assistant", "agent"]:
            return "assistant"

        return "assistant"

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
- If the user is an admin, help with platform overview and operational guidance.
- Do not invent fake experience for candidates.
- Do not invent platform data.
- If platform data is not available, say what is missing.
- Keep answers clear, useful, and professional.

Available user context:
%s
""" % context

        messages = [
            {
                "role": "system",
                "content": system_prompt.strip(),
            }
        ]

        recent_messages = session.messages.order_by("-created_at")[:10]
        recent_messages = reversed(list(recent_messages))

        for message in recent_messages:
            role = ChatbotService.normalize_role(message.role)

            if not message.content:
                continue

            messages.append(
                {
                    "role": role,
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
        messages = cls.build_messages(
            user=user,
            session=session,
            user_message=user_message,
        )

        return AIService.ask_text(
            messages=messages,
            max_output_tokens=1000,
        )