from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import JobApplication, JobPost, Profile, Resume
from .services.rag_service import RAGService
from .services.rag_sync_service import RAGSyncService


@receiver(post_save, sender=Resume)
def index_resume_to_rag(sender, instance, created, **kwargs):
    transaction.on_commit(
        lambda: RAGSyncService.index_resume(instance)
    )


@receiver(post_delete, sender=Resume)
def delete_resume_from_rag(sender, instance, **kwargs):
    transaction.on_commit(
        lambda: RAGService.delete_record("resume", instance.id)
    )


@receiver(post_save, sender=JobPost)
def index_job_to_rag(sender, instance, created, **kwargs):
    transaction.on_commit(
        lambda: RAGSyncService.index_job_post(instance)
    )


@receiver(post_delete, sender=JobPost)
def delete_job_from_rag(sender, instance, **kwargs):
    transaction.on_commit(
        lambda: RAGService.delete_record("recruiter_job", instance.id)
    )


@receiver(post_save, sender=JobApplication)
def index_application_to_rag(sender, instance, created, **kwargs):
    transaction.on_commit(
        lambda: RAGSyncService.index_job_application(instance)
    )


@receiver(post_delete, sender=JobApplication)
def delete_application_from_rag(sender, instance, **kwargs):
    transaction.on_commit(
        lambda: RAGService.delete_record("job_application", instance.id)
    )


@receiver(post_save, sender=Profile)
def index_company_profile_to_rag(sender, instance, created, **kwargs):
    if instance.role == Profile.ROLE_RECRUITER:
        transaction.on_commit(
            lambda: RAGSyncService.index_company_profile(instance)
        )


@receiver(post_delete, sender=Profile)
def delete_company_profile_from_rag(sender, instance, **kwargs):
    transaction.on_commit(
        lambda: RAGService.delete_record("company_profile", instance.id)
    )