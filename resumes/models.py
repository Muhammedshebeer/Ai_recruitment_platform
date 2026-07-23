from django.conf import settings
from django.db import models
from django.utils import timezone


class Profile(models.Model):

    ROLE_JOB_SEEKER = "job_seeker"
    ROLE_RECRUITER = "recruiter"

    ROLE_CHOICES = (
        (ROLE_JOB_SEEKER, "Job Seeker"),
        (ROLE_RECRUITER, "Recruiter"),
    )

    RECRUITER_PENDING = "pending"
    RECRUITER_APPROVED = "approved"
    RECRUITER_REJECTED = "rejected"
    RECRUITER_BLOCKED = "blocked"

    RECRUITER_STATUS_CHOICES = (
        (RECRUITER_PENDING, "Pending"),
        (RECRUITER_APPROVED, "Approved"),
        (RECRUITER_REJECTED, "Rejected"),
        (RECRUITER_BLOCKED, "Blocked"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_JOB_SEEKER,
    )

    recruiter_status = models.CharField(
        max_length=20,
        choices=RECRUITER_STATUS_CHOICES,
        default=RECRUITER_PENDING,   # IMPORTANT: new recruiter should be pending
    )

    recruiter_status_note = models.TextField(
        blank=True,
    )

    company_name = models.CharField(
        max_length=255,
        blank=True,
    )

    company_about = models.TextField(
        blank=True,
    )

    company_website = models.URLField(
        blank=True,
    )

    company_location = models.CharField(
        max_length=255,
        blank=True,
    )

    company_logo = models.ImageField(
        upload_to="company_logos/",
        blank=True,
        null=True,
    )

    company_document = models.FileField(
        upload_to="company_documents/",
        blank=True,
        null=True,
    )

    company_document_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Trade license, company registration, tax certificate, etc.",
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
    )

    headline = models.CharField(
        max_length=255,
        blank=True,
    )

    location = models.CharField(
        max_length=255,
        blank=True,
    )

    about = models.TextField(
        blank=True,
    )

    linkedin_url = models.URLField(
        blank=True,
    )

    portfolio_url = models.URLField(
        blank=True,
    )

    is_searchable = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_approved_recruiter(self):
        return (
            self.role == self.ROLE_RECRUITER
            and self.recruiter_status == self.RECRUITER_APPROVED
        )


class Resume(models.Model):
    EXPERIENCE_ENTRY = "entry"
    EXPERIENCE_JUNIOR = "junior"
    EXPERIENCE_MID = "mid"
    EXPERIENCE_SENIOR = "senior"
    EXPERIENCE_MANAGER = "manager"

    EXPERIENCE_LEVEL_CHOICES = (
        (EXPERIENCE_ENTRY, "Entry Level"),
        (EXPERIENCE_JUNIOR, "Junior"),
        (EXPERIENCE_MID, "Mid Level"),
        (EXPERIENCE_SENIOR, "Senior"),
        (EXPERIENCE_MANAGER, "Manager"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resumes",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)

    pdf = models.FileField(upload_to="resumes/")

    target_job_title = models.CharField(max_length=255, blank=True)

    target_experience_level = models.CharField(
        max_length=30,
        choices=EXPERIENCE_LEVEL_CHOICES,
        blank=True,
    )

    target_location = models.CharField(max_length=255, blank=True)

    target_job_description = models.TextField(blank=True)

    extracted_text = models.TextField(blank=True)

    ai_response = models.JSONField(null=True, blank=True)

    ats_score = models.IntegerField(null=True, blank=True)

    summary = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_ai_value(self, key, default=None):
        if default is None:
            default = []

        if isinstance(self.ai_response, dict):
            return self.ai_response.get(key, default)

        return default

    @property
    def skills(self):
        return self.get_ai_value("skills", [])

    @property
    def missing_skills(self):
        return self.get_ai_value("missing_skills", [])

    @property
    def strengths(self):
        return self.get_ai_value("strengths", [])

    @property
    def improvements(self):
        return self.get_ai_value("improvements", [])

    @property
    def things_to_add(self):
        return self.get_ai_value("things_to_add", [])

    @property
    def resume_bullet_points(self):
        return self.get_ai_value("resume_bullet_points", [])

    @property
    def keywords_to_add(self):
        return self.get_ai_value("keywords_to_add", [])

    @property
    def weak_sections(self):
        return self.get_ai_value("weak_sections", [])

    @property
    def improved_summary(self):
        if isinstance(self.ai_response, dict):
            return self.ai_response.get("improved_summary", "")
        return ""

    @property
    def job_match_feedback(self):
        if isinstance(self.ai_response, dict):
            return self.ai_response.get("job_match_feedback", "")
        return ""

    @property
    def job_match_score(self):
        if isinstance(self.ai_response, dict):
            return self.ai_response.get("job_match_score", 0)
        return 0


class JobPost(models.Model):
    JOB_TYPE_FULL_TIME = "full_time"
    JOB_TYPE_PART_TIME = "part_time"
    JOB_TYPE_CONTRACT = "contract"
    JOB_TYPE_INTERNSHIP = "internship"
    JOB_TYPE_REMOTE = "remote"

    JOB_TYPE_CHOICES = (
        (JOB_TYPE_FULL_TIME, "Full Time"),
        (JOB_TYPE_PART_TIME, "Part Time"),
        (JOB_TYPE_CONTRACT, "Contract"),
        (JOB_TYPE_INTERNSHIP, "Internship"),
        (JOB_TYPE_REMOTE, "Remote"),
    )

    STATUS_DRAFT = "draft"
    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_OPEN, "Open"),
        (STATUS_CLOSED, "Closed"),
    )

    recruiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posted_jobs",
    )

    title = models.CharField(max_length=255)

    company_name = models.CharField(max_length=255)

    location = models.CharField(max_length=255)

    job_type = models.CharField(
        max_length=30,
        choices=JOB_TYPE_CHOICES,
        default=JOB_TYPE_FULL_TIME,
    )

    description = models.TextField()

    requirements = models.TextField(blank=True)

    responsibilities = models.TextField(blank=True)

    skills_required = models.JSONField(default=list, blank=True)

    salary_min = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    salary_max = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )

    deadline = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "%s - %s" % (self.title, self.company_name)

    @property
    def is_open(self):
        if self.status != self.STATUS_OPEN:
            return False

        if self.deadline and self.deadline < timezone.localdate():
            return False

        return True

    @property
    def applications_count(self):
        return self.applications.count()


class JobApplication(models.Model):
    STATUS_SUBMITTED = "submitted"
    STATUS_REVIEWED = "reviewed"
    STATUS_SHORTLISTED = "shortlisted"
    STATUS_INTERVIEW = "interview"
    STATUS_REJECTED = "rejected"
    STATUS_HIRED = "hired"

    STATUS_CHOICES = (
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_SHORTLISTED, "Shortlisted"),
        (STATUS_INTERVIEW, "Interview Scheduled"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_HIRED, "Hired"),
    )

    job = models.ForeignKey(
        JobPost,
        on_delete=models.CASCADE,
        related_name="applications",
    )

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_applications",
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_applications",
    )

    full_name = models.CharField(max_length=255)

    email = models.EmailField()

    phone = models.CharField(max_length=50, blank=True)

    cover_letter = models.TextField(blank=True)

    match_score = models.IntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
    )

    recruiter_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("job", "applicant")

    def __str__(self):
        return "%s applied for %s" % (self.full_name, self.job.title)


class SavedJob(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_jobs",
    )

    job = models.ForeignKey(
        JobPost,
        on_delete=models.CASCADE,
        related_name="saved_by_users",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("user", "job")

    def __str__(self):
        return "%s saved %s" % (self.user.username, self.job.title)


class CoverLetter(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cover_letters",
    )

    job = models.ForeignKey(
        JobPost,
        on_delete=models.CASCADE,
        related_name="cover_letters",
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cover_letters",
    )

    title = models.CharField(max_length=255)

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class InterviewQuestionSet(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_question_sets",
    )

    job = models.ForeignKey(
        JobPost,
        on_delete=models.CASCADE,
        related_name="interview_question_sets",
    )

    resume = models.ForeignKey(
        Resume,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_question_sets",
    )

    title = models.CharField(max_length=255)

    ai_response = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_ai_value(self, key, default=None):
        if default is None:
            default = []

        if isinstance(self.ai_response, dict):
            return self.ai_response.get(key, default)

        return default

    @property
    def technical_questions(self):
        return self.get_ai_value("technical_questions", [])

    @property
    def hr_questions(self):
        return self.get_ai_value("hr_questions", [])

    @property
    def suggested_answers(self):
        return self.get_ai_value("suggested_answers", [])

    @property
    def preparation_tips(self):
        return self.get_ai_value("preparation_tips", [])



class ReportedJob(models.Model):
    REASON_SPAM = "spam"
    REASON_FAKE = "fake"
    REASON_INAPPROPRIATE = "inappropriate"
    REASON_OTHER = "other"

    REASON_CHOICES = (
        (REASON_SPAM, "Spam"),
        (REASON_FAKE, "Fake Job"),
        (REASON_INAPPROPRIATE, "Inappropriate Content"),
        (REASON_OTHER, "Other"),
    )

    STATUS_OPEN = "open"
    STATUS_REVIEWED = "reviewed"
    STATUS_RESOLVED = "resolved"
    STATUS_DISMISSED = "dismissed"

    STATUS_CHOICES = (
        (STATUS_OPEN, "Open"),
        (STATUS_REVIEWED, "Reviewed"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_DISMISSED, "Dismissed"),
    )

    job = models.ForeignKey(
        JobPost,
        on_delete=models.CASCADE,
        related_name="reports",
    )

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reported_jobs",
    )

    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        default=REASON_OTHER,
    )

    details = models.TextField(blank=True)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )

    admin_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "%s - %s" % (self.job.title, self.get_reason_display())



# for ai chatbot #

class ChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
    )

    title = models.CharField(
        max_length=255,
        default="New Chat",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return "%s - %s" % (self.user.username, self.title)


class ChatMessage(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"

    ROLE_CHOICES = (
        (ROLE_USER, "User"),
        (ROLE_ASSISTANT, "Assistant"),
    )

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
    )

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return "%s - %s" % (self.role, self.content[:50])



# for ai agent #

class AgentSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_sessions",
    )

    title = models.CharField(
        max_length=255,
        default="New Agent Chat",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return "%s - %s" % (self.user.username, self.title)


class AgentMessage(models.Model):
    ROLE_USER = "user"
    ROLE_AGENT = "agent"
    ROLE_TOOL = "tool"

    ROLE_CHOICES = (
        (ROLE_USER, "User"),
        (ROLE_AGENT, "Agent"),
        (ROLE_TOOL, "Tool"),
    )

    session = models.ForeignKey(
        AgentSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
    )

    content = models.TextField()

    tool_name = models.CharField(
        max_length=100,
        blank=True,
    )

    tool_result = models.JSONField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return "%s - %s" % (self.role, self.content[:50])


class AgentActionLog(models.Model):
    STATUS_PROPOSED = "proposed"
    STATUS_CONFIRMED = "confirmed"
    STATUS_REJECTED = "rejected"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_PROPOSED, "Proposed"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_action_logs",
    )

    action_name = models.CharField(max_length=100)

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PROPOSED,
    )

    input_data = models.JSONField(default=dict, blank=True)

    result_data = models.JSONField(default=dict, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s - %s" % (self.action_name, self.status)

