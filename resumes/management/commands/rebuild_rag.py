from django.core.management.base import BaseCommand

from resumes.models import JobApplication, JobPost, Profile, Resume
from resumes.services.rag_sync_service import RAGSyncService


class Command(BaseCommand):
    help = "Rebuild RAG vector database from existing platform records."

    def handle(self, *args, **options):
        resume_count = 0
        job_count = 0
        application_count = 0
        company_count = 0

        self.stdout.write("Indexing resumes...")
        for resume in Resume.objects.select_related("user").all():
            RAGSyncService.index_resume(resume)
            resume_count += 1

        self.stdout.write("Indexing jobs...")
        for job in JobPost.objects.select_related("recruiter").all():
            RAGSyncService.index_job_post(job)
            job_count += 1

        self.stdout.write("Indexing applications...")
        for application in JobApplication.objects.select_related(
            "applicant",
            "job",
            "resume",
        ).all():
            RAGSyncService.index_job_application(application)
            application_count += 1

        self.stdout.write("Indexing company profiles...")
        for profile in Profile.objects.select_related("user").filter(
            role=Profile.ROLE_RECRUITER
        ):
            RAGSyncService.index_company_profile(profile)
            company_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "RAG rebuild completed. "
                f"Resumes: {resume_count}, "
                f"Jobs: {job_count}, "
                f"Applications: {application_count}, "
                f"Companies: {company_count}"
            )
        )