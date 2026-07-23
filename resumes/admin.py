from django.contrib import admin

from .models import (
    CoverLetter,
    InterviewQuestionSet,
    JobApplication,
    JobPost,
    Profile,
    Resume,
    SavedJob,
    ReportedJob,
    AgentActionLog,
AgentMessage,
AgentSession,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "company_name", "phone", "created_at")
    search_fields = ("user__username", "user__email", "company_name", "phone")
    list_filter = ("role", "created_at")


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "target_job_title", "ats_score", "created_at")
    search_fields = ("title", "summary", "target_job_title", "user__username", "user__email")
    list_filter = ("created_at", "ats_score", "target_experience_level", "user")
    readonly_fields = ("created_at", "updated_at")


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "company_name", "location", "job_type", "status", "recruiter", "created_at")
    search_fields = ("title", "company_name", "location", "description")
    list_filter = ("status", "job_type", "created_at")


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "applicant", "full_name", "match_score", "status", "created_at")
    search_fields = ("full_name", "email", "job__title", "applicant__username")
    list_filter = ("status", "created_at", "job")


@admin.register(ReportedJob)
class ReportedJobAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "reason", "status", "reporter", "created_at")
    search_fields = ("job__title", "details", "reporter__username")
    list_filter = ("reason", "status", "created_at")


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "job", "created_at")
    search_fields = ("user__username", "job__title", "job__company_name")
    list_filter = ("created_at",)


@admin.register(CoverLetter)
class CoverLetterAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "job", "resume", "created_at")
    search_fields = ("title", "user__username", "job__title", "content")
    list_filter = ("created_at",)


@admin.register(InterviewQuestionSet)
class InterviewQuestionSetAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "job", "resume", "created_at")
    search_fields = ("title", "user__username", "job__title")
    list_filter = ("created_at",)
    
    
@admin.register(AgentSession)
class AgentSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "created_at", "updated_at")
    search_fields = ("user__username", "title")
    list_filter = ("created_at",)


@admin.register(AgentMessage)
class AgentMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "tool_name", "created_at")
    search_fields = ("content", "tool_name", "session__user__username")
    list_filter = ("role", "created_at")


@admin.register(AgentActionLog)
class AgentActionLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "action_name", "status", "created_at")
    search_fields = ("user__username", "action_name", "notes")
    list_filter = ("status", "action_name", "created_at")    
