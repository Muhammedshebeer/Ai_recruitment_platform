from django.db.models import Count, Q

from ..models import (
    AgentActionLog,
    JobApplication,
    JobPost,
    Profile,
    Resume,
)
from .job_matching_services import JobMatchingService
from .rag_service import RAGService


class RecruitmentAgentTools:

    @staticmethod
    def get_user_role(user):
        if user.is_staff:
            return "admin"

        profile = getattr(user, "profile", None)

        if not profile:
            return "unknown"

        return profile.role

    @classmethod
    def latest_resume_summary(cls, user, arguments=None):
        resume = Resume.objects.filter(
            user=user
        ).order_by("-created_at").first()

        if not resume:
            return {
                "success": False,
                "message": "No resume found. Please upload and analyze a resume first.",
            }

        return {
            "success": True,
            "resume_id": resume.id,
            "title": resume.title,
            "ats_score": resume.ats_score or 0,
            "job_match_score": resume.job_match_score or 0,
            "target_job_title": resume.target_job_title,
            "summary": resume.summary,
            "skills": resume.skills,
            "missing_skills": resume.missing_skills,
            "things_to_add": resume.things_to_add,
            "keywords_to_add": resume.keywords_to_add,
        }

    @classmethod
    def suggest_jobs_for_user(cls, user, arguments=None):
        resume = Resume.objects.filter(
            user=user
        ).order_by("-created_at").first()

        if not resume:
            return {
                "success": False,
                "message": "No analyzed resume found. Upload a resume first.",
            }

        matched_jobs = JobMatchingService.match_jobs_for_resume(
            resume,
            limit=10,
        )

        jobs = []

        for item in matched_jobs:
            job = item["job"]

            jobs.append(
                {
                    "job_id": job.id,
                    "title": job.title,
                    "company_name": job.company_name,
                    "location": job.location,
                    "job_type": job.get_job_type_display(),
                    "match_score": item["score"],
                    "skills_required": job.skills_required,
                }
            )

        return {
            "success": True,
            "resume_title": resume.title,
            "jobs": jobs,
        }

    @classmethod
    def my_applications(cls, user, arguments=None):
        applications = JobApplication.objects.filter(
            applicant=user
        ).select_related("job").order_by("-created_at")[:10]

        data = []

        for application in applications:
            data.append(
                {
                    "application_id": application.id,
                    "job_title": application.job.title,
                    "company_name": application.job.company_name,
                    "status": application.get_status_display(),
                    "match_score": application.match_score or 0,
                    "applied_on": application.created_at.strftime("%d %b %Y"),
                }
            )

        return {
            "success": True,
            "applications": data,
        }

    @classmethod
    def recruiter_jobs(cls, user, arguments=None):
        jobs = JobPost.objects.filter(
            recruiter=user
        ).annotate(
            total_applications=Count("applications")
        ).order_by("-created_at")[:10]

        data = []

        for job in jobs:
            data.append(
                {
                    "job_id": job.id,
                    "title": job.title,
                    "company_name": job.company_name,
                    "status": job.get_status_display(),
                    "location": job.location,
                    "total_applications": job.total_applications,
                    "created_at": job.created_at.strftime("%d %b %Y"),
                }
            )

        return {
            "success": True,
            "jobs": data,
        }

    @classmethod
    def rank_candidates_for_job(cls, user, arguments=None):
        arguments = arguments or {}

        job_id = arguments.get("job_id")

        if not job_id:
            return {
                "success": False,
                "message": "job_id is required to rank candidates.",
            }

        try:
            job = JobPost.objects.get(
                id=job_id,
                recruiter=user,
            )
        except JobPost.DoesNotExist:
            return {
                "success": False,
                "message": "Job not found or you do not have access to this job.",
            }

        applications = JobApplication.objects.filter(
            job=job
        ).select_related(
            "applicant",
            "resume",
        ).order_by("-match_score", "-created_at")

        candidates = []

        for application in applications:
            resume = application.resume

            candidates.append(
                {
                    "application_id": application.id,
                    "candidate_name": application.full_name,
                    "email": application.email,
                    "status": application.get_status_display(),
                    "match_score": application.match_score or 0,
                    "resume_title": resume.title if resume else "",
                    "ats_score": resume.ats_score if resume else 0,
                    "skills": resume.skills if resume else [],
                    "missing_skills": resume.missing_skills if resume else [],
                    "summary": resume.summary if resume else "",
                }
            )

        return {
            "success": True,
            "job_id": job.id,
            "job_title": job.title,
            "total_candidates": len(candidates),
            "candidates": candidates,
        }

    @classmethod
    def platform_summary(cls, user, arguments=None):
        if not user.is_staff:
            return {
                "success": False,
                "message": "Only admin users can access platform summary.",
            }

        return {
            "success": True,
            "total_job_seekers": Profile.objects.filter(
                role=Profile.ROLE_JOB_SEEKER
            ).count(),
            "total_recruiters": Profile.objects.filter(
                role=Profile.ROLE_RECRUITER
            ).count(),
            "pending_recruiters": Profile.objects.filter(
                role=Profile.ROLE_RECRUITER,
                recruiter_status=Profile.RECRUITER_PENDING,
            ).count(),
            "total_resumes": Resume.objects.count(),
            "total_jobs": JobPost.objects.count(),
            "open_jobs": JobPost.objects.filter(
                status=JobPost.STATUS_OPEN
            ).count(),
            "total_applications": JobApplication.objects.count(),
        }

    @classmethod
    def propose_shortlist_candidate(cls, user, arguments=None):
        arguments = arguments or {}

        application_id = arguments.get("application_id")

        if not application_id:
            return {
                "success": False,
                "message": "application_id is required.",
            }

        try:
            application = JobApplication.objects.get(
                id=application_id,
                job__recruiter=user,
            )
        except JobApplication.DoesNotExist:
            return {
                "success": False,
                "message": "Application not found or you do not have access.",
            }

        action = AgentActionLog.objects.create(
            user=user,
            action_name="shortlist_candidate",
            input_data={
                "application_id": application.id,
                "candidate_name": application.full_name,
                "job_title": application.job.title,
            },
            result_data={},
            notes="Agent proposed shortlisting this candidate.",
        )

        return {
            "success": True,
            "confirmation_required": True,
            "action_id": action.id,
            "message": (
                "I can shortlist %s for %s. Please confirm before I update the application."
                % (
                    application.full_name,
                    application.job.title,
                )
            ),
        }

    TOOL_MAP = {
        "latest_resume_summary": latest_resume_summary,
        "suggest_jobs_for_user": suggest_jobs_for_user,
        "my_applications": my_applications,
        "recruiter_jobs": recruiter_jobs,
        "rank_candidates_for_job": rank_candidates_for_job,
        "platform_summary": platform_summary,
        "propose_shortlist_candidate": propose_shortlist_candidate,
    }

    @classmethod
    def run_tool(cls, tool_name, user, arguments=None):
        tool_map = {
            "latest_resume_summary": cls.latest_resume_summary,
            "suggest_jobs_for_user": cls.suggest_jobs_for_user,
            "my_applications": cls.my_applications,
            "recruiter_jobs": cls.recruiter_jobs,
            "rank_candidates_for_job": cls.rank_candidates_for_job,
            "platform_summary": cls.platform_summary,
            "propose_shortlist_candidate": cls.propose_shortlist_candidate,

            # RAG tool
            "rag_search_platform_knowledge": cls.rag_search_platform_knowledge,
        }

        tool = tool_map.get(tool_name)

        if not tool:
            return {
                "success": False,
                "message": "Unknown tool: %s" % tool_name,
            }

        return tool(user, arguments)
    
    
    @classmethod
    def rag_search_platform_knowledge(cls, user, arguments=None):
        arguments = arguments or {}

        query = arguments.get("query", "")
        top_k = int(arguments.get("top_k", 8))

        if not query:
            return {
                "success": False,
                "message": "Query is required for RAG search.",
            }

        results = RAGService.search(
            query=query,
            user=user,
            top_k=top_k,
        )

        return {
            "success": True,
            "source": "rag_vector_database",
            "query": query,
            "results_count": len(results),
            "results": results,
        }