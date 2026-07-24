from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Avg, Count, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from django.http import JsonResponse

from .forms import (
    CandidateProfileForm,
    CompanyProfileForm,
    JobApplicationForm,
    JobPostForm,
    RecruiterRegisterForm,
    RegisterForm,
    ReportJobForm,
    ResumeSelectForm,
    ResumeUploadForm,
)
from .models import (
    CoverLetter,
    InterviewQuestionSet,
    JobApplication,
    JobPost,
    Profile,
    ReportedJob,
    Resume,
    SavedJob,
    ChatSession,
    ChatMessage,
    AgentActionLog, AgentMessage, AgentSession, JobApplication
)
from .services.career_tool_service import CareerToolsService
from .services.email_service import EmailService
from .services.job_matching_services import JobMatchingService
from .services.resume_analysis_service import ResumeAnalysisService
from .services.chatbot_service import ChatbotService
from .services.agent_service import RecruitmentAgentService


def get_or_create_profile(user, default_role=Profile.ROLE_JOB_SEEKER):
    profile, created = Profile.objects.get_or_create(
        user=user,
        defaults={"role": default_role},
    )
    return profile


def is_platform_admin(user):
    return user.is_authenticated and user.is_staff


def is_recruiter(user):
    if not user.is_authenticated:
        return False

    profile = get_or_create_profile(user)
    return profile.role == Profile.ROLE_RECRUITER


def is_job_seeker(user):
    if not user.is_authenticated:
        return False

    profile = get_or_create_profile(user)
    return profile.role == Profile.ROLE_JOB_SEEKER


def recruiter_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("recruiter_login")

        if not is_recruiter(request.user):
            messages.error(request, "Recruiter access required.")
            return redirect("dashboard")

        profile = get_or_create_profile(request.user)

        if profile.recruiter_status != Profile.RECRUITER_APPROVED:
            return redirect("recruiter_pending_status")

        return view_func(request, *args, **kwargs)

    return wrapper


def job_seeker_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if not is_job_seeker(request.user):
            messages.error(request, "Job seeker access required.")
            return redirect("recruiter_dashboard")

        return view_func(request, *args, **kwargs)

    return wrapper


def add_auth_form_classes(form):
    form.fields["username"].widget.attrs.update({
        "class": "w-full rounded-xl bg-slate-900 border border-slate-700 px-5 py-4 outline-none focus:border-blue-500",
        "placeholder": "Username",
    })

    form.fields["password"].widget.attrs.update({
        "class": "w-full rounded-xl bg-slate-900 border border-slate-700 px-5 py-4 outline-none focus:border-blue-500",
        "placeholder": "Password",
    })

    return form


def home(request):
    recent_jobs = JobPost.objects.filter(
        status=JobPost.STATUS_OPEN,
    ).order_by("-created_at")[:6]

    return render(request, "home.html", {"recent_jobs": recent_jobs})


def register_user(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect("dashboard")
    else:
        form = RegisterForm()

    return render(request, "resumes/register.html", {"form": form})


def recruiter_register(request):
    if request.user.is_authenticated:
        return redirect("recruiter_dashboard")

    if request.method == "POST":
        form = RecruiterRegisterForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            user = form.save()

            EmailService.recruiter_pending_notice(user)

            login(request, user)

            messages.success(
                request,
                "Recruiter account created successfully. Your account is pending admin approval."
            )

            return redirect("recruiter_pending_status")
    else:
        form = RecruiterRegisterForm()

    return render(
        request,
        "resumes/recruiter/register.html",
        {
            "form": form,
        },
    )


def login_user(request):
    if request.user.is_authenticated:
        if is_recruiter(request.user):
            return redirect("recruiter_dashboard")

        return redirect("dashboard")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        add_auth_form_classes(form)

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if is_recruiter(user):
                return redirect("recruiter_dashboard")

            return redirect("dashboard")
    else:
        form = add_auth_form_classes(AuthenticationForm())

    return render(request, "resumes/login.html", {"form": form})


def recruiter_login(request):
    if request.user.is_authenticated:
        return redirect("recruiter_dashboard")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        add_auth_form_classes(form)

        if form.is_valid():
            user = form.get_user()
            profile = get_or_create_profile(user)

            if profile.role != Profile.ROLE_RECRUITER:
                form.add_error(None, "This account is not a recruiter account.")
            else:
                login(request, user)

                if profile.recruiter_status != Profile.RECRUITER_APPROVED:
                    return redirect("recruiter_pending_status")

                return redirect("recruiter_dashboard")
    else:
        form = add_auth_form_classes(AuthenticationForm())

    return render(request, "resumes/recruiter/login.html", {"form": form})


def logout_user(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("home")


@login_required
def recruiter_pending_status(request):
    profile = get_or_create_profile(request.user)

    if profile.role != Profile.ROLE_RECRUITER:
        return redirect("dashboard")

    if profile.recruiter_status == Profile.RECRUITER_APPROVED:
        return redirect("recruiter_dashboard")

    return render(
        request,
        "resumes/recruiter/pending_status.html",
        {
            "profile": profile,
        },
    )


@login_required
@job_seeker_required
def dashboard(request):
    resumes = Resume.objects.filter(user=request.user)

    total_resumes = resumes.count()
    highest_score = resumes.aggregate(Max("ats_score")).get("ats_score__max") or 0
    average_score = resumes.aggregate(Avg("ats_score")).get("ats_score__avg") or 0
    recent_resumes = resumes.order_by("-created_at")[:5]

    latest_resume = resumes.order_by("-created_at").first()
    matched_jobs = []

    if latest_resume:
        matched_jobs = JobMatchingService.match_jobs_for_resume(
            latest_resume,
            limit=5,
        )

    applications = JobApplication.objects.filter(
        applicant=request.user,
    ).select_related("job").order_by("-created_at")[:5]

    saved_jobs = SavedJob.objects.filter(
        user=request.user,
    ).select_related("job").order_by("-created_at")[:5]

    cover_letters_count = CoverLetter.objects.filter(user=request.user).count()
    interview_sets_count = InterviewQuestionSet.objects.filter(user=request.user).count()

    score_chart_labels = []
    ats_chart_data = []
    match_chart_data = []

    for resume in resumes.order_by("created_at"):
        score_chart_labels.append(resume.created_at.strftime("%d %b"))
        ats_chart_data.append(resume.ats_score or 0)
        match_chart_data.append(resume.job_match_score or 0)

    application_status_counts = {}

    for status_value, status_label in JobApplication.STATUS_CHOICES:
        application_status_counts[status_value] = JobApplication.objects.filter(
            applicant=request.user,
            status=status_value,
        ).count()

    return render(
        request,
        "resumes/dashboard.html",
        {
            "total_resumes": total_resumes,
            "highest_score": int(highest_score or 0),
            "average_score": int(average_score or 0),
            "recent_resumes": recent_resumes,
            "matched_jobs": matched_jobs,
            "applications": applications,
            "saved_jobs": saved_jobs,
            "cover_letters_count": cover_letters_count,
            "interview_sets_count": interview_sets_count,
            "score_chart_labels": score_chart_labels,
            "ats_chart_data": ats_chart_data,
            "match_chart_data": match_chart_data,
            "application_status_counts": application_status_counts,
        },
    )


@login_required
@job_seeker_required
def candidate_profile_settings(request):
    profile = get_or_create_profile(request.user)

    if request.method == "POST":
        form = CandidateProfileForm(request.POST, instance=profile)

        if form.is_valid():
            form.save()
            messages.success(request, "Candidate profile updated successfully.")
            return redirect("candidate_profile_settings")
    else:
        form = CandidateProfileForm(instance=profile)

    return render(
        request,
        "resumes/candidates/profile_settings.html",
        {
            "form": form,
        },
    )


@login_required
@job_seeker_required
def upload_resume(request):
    if request.method == "POST":
        form = ResumeUploadForm(request.POST, request.FILES)

        if form.is_valid():
            resume = form.save(commit=False)
            resume.user = request.user
            resume.save()

            try:
                ResumeAnalysisService.analyze(resume)
            except Exception as exc:
                messages.error(
                    request,
                    "Resume uploaded, but AI analysis failed: %s" % exc,
                )
                return render(
                    request,
                    "resumes/upload.html",
                    {
                        "form": form,
                        "resume": resume,
                    },
                )

            return redirect("resume_result", resume_id=resume.id)

    else:
        form = ResumeUploadForm()

    return render(request, "resumes/upload.html", {"form": form})


@login_required
@job_seeker_required
def resume_result(request, resume_id):
    resume = get_object_or_404(
        Resume,
        id=resume_id,
        user=request.user,
    )

    matched_jobs = JobMatchingService.match_jobs_for_resume(
        resume,
        limit=8,
    )

    return render(
        request,
        "resumes/result.html",
        {
            "resume": resume,
            "matched_jobs": matched_jobs,
        },
    )


@login_required
@job_seeker_required
def resume_history(request):
    resumes = Resume.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "resumes/history.html", {"resumes": resumes})


def job_list(request):
    jobs = JobPost.objects.filter(status=JobPost.STATUS_OPEN)

    q = request.GET.get("q", "").strip()
    job_type = request.GET.get("job_type", "").strip()
    location = request.GET.get("location", "").strip()
    skill = request.GET.get("skill", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    salary_min = request.GET.get("salary_min", "").strip()
    salary_max = request.GET.get("salary_max", "").strip()

    if q:
        jobs = jobs.filter(
            Q(title__icontains=q)
            | Q(company_name__icontains=q)
            | Q(location__icontains=q)
            | Q(description__icontains=q)
            | Q(requirements__icontains=q)
        )

    if job_type:
        jobs = jobs.filter(job_type=job_type)

    if location:
        jobs = jobs.filter(location__icontains=location)

    if skill:
        jobs = jobs.filter(skills_required__icontains=skill)

    if date_from:
        jobs = jobs.filter(created_at__date__gte=date_from)

    if date_to:
        jobs = jobs.filter(created_at__date__lte=date_to)

    if salary_min:
        jobs = jobs.filter(
            Q(salary_max__gte=salary_min)
            | Q(salary_min__gte=salary_min)
        )

    if salary_max:
        jobs = jobs.filter(
            Q(salary_min__lte=salary_max)
            | Q(salary_max__lte=salary_max)
        )

    jobs = jobs.annotate(
        total_applications=Count("applications"),
    ).order_by("-created_at")

    saved_job_ids = []

    if request.user.is_authenticated:
        saved_job_ids = list(
            SavedJob.objects.filter(
                user=request.user,
            ).values_list("job_id", flat=True)
        )

    return render(
        request,
        "resumes/jobs/list.html",
        {
            "jobs": jobs,
            "q": q,
            "job_type": job_type,
            "location": location,
            "skill": skill,
            "date_from": date_from,
            "date_to": date_to,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "job_type_choices": JobPost.JOB_TYPE_CHOICES,
            "saved_job_ids": saved_job_ids,
        },
    )


def job_detail(request, job_id):
    job = get_object_or_404(
        JobPost,
        id=job_id,
        status=JobPost.STATUS_OPEN,
    )

    already_applied = False
    is_saved = False

    if request.user.is_authenticated:
        already_applied = JobApplication.objects.filter(
            job=job,
            applicant=request.user,
        ).exists()

        is_saved = SavedJob.objects.filter(
            job=job,
            user=request.user,
        ).exists()

    return render(
        request,
        "resumes/jobs/detail.html",
        {
            "job": job,
            "already_applied": already_applied,
            "is_saved": is_saved,
        },
    )


@login_required
@job_seeker_required
def apply_job(request, job_id):
    job = get_object_or_404(
        JobPost,
        id=job_id,
        status=JobPost.STATUS_OPEN,
    )

    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.error(request, "You already applied for this job.")
        return redirect("job_detail", job_id=job.id)

    if not Resume.objects.filter(user=request.user).exists():
        messages.error(
            request,
            "Please upload and analyze your resume before applying.",
        )
        return redirect("upload_resume")

    if request.method == "POST":
        form = JobApplicationForm(
            request.POST,
            user=request.user,
            job=job,
        )

        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user

            if application.resume:
                application.match_score = JobMatchingService.calculate_match_score(
                    application.resume,
                    job,
                )

            application.save()

            EmailService.application_submitted(application)

            messages.success(request, "Application submitted successfully.")
            return redirect("dashboard")
    else:
        form = JobApplicationForm(
            user=request.user,
            job=job,
        )

    return render(
        request,
        "resumes/jobs/apply.html",
        {
            "job": job,
            "form": form,
        },
    )


@login_required
@job_seeker_required
def toggle_saved_job(request, job_id):
    job = get_object_or_404(
        JobPost,
        id=job_id,
        status=JobPost.STATUS_OPEN,
    )

    saved_job = SavedJob.objects.filter(
        user=request.user,
        job=job,
    ).first()

    if saved_job:
        saved_job.delete()
        messages.success(request, "Job removed from saved jobs.")
    else:
        SavedJob.objects.create(
            user=request.user,
            job=job,
        )
        messages.success(request, "Job saved successfully.")

    next_url = request.META.get("HTTP_REFERER")

    if next_url:
        return redirect(next_url)

    return redirect("job_detail", job_id=job.id)


@login_required
@job_seeker_required
def saved_jobs(request):
    saved_jobs_list = SavedJob.objects.filter(
        user=request.user,
    ).select_related("job").order_by("-created_at")

    return render(
        request,
        "resumes/jobs/saved_jobs.html",
        {
            "saved_jobs": saved_jobs_list,
        },
    )


def companies(request):
    company_profiles = Profile.objects.filter(
        role=Profile.ROLE_RECRUITER,
        recruiter_status=Profile.RECRUITER_APPROVED,
    ).exclude(company_name="").select_related("user").order_by("company_name")

    return render(
        request,
        "resumes/companies/list.html",
        {
            "company_profiles": company_profiles,
        },
    )


def company_detail(request, profile_id):
    profile = get_object_or_404(
        Profile.objects.select_related("user"),
        id=profile_id,
        role=Profile.ROLE_RECRUITER,
        recruiter_status=Profile.RECRUITER_APPROVED,
    )

    jobs = JobPost.objects.filter(
        recruiter=profile.user,
        status=JobPost.STATUS_OPEN,
    ).order_by("-created_at")

    return render(
        request,
        "resumes/companies/detail.html",
        {
            "profile": profile,
            "jobs": jobs,
        },
    )


@login_required
def report_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)

    if request.method == "POST":
        form = ReportJobForm(request.POST)

        if form.is_valid():
            report = form.save(commit=False)
            report.job = job
            report.reporter = request.user if request.user.is_authenticated else None
            report.save()

            messages.success(
                request,
                "Thank you. This job report has been submitted.",
            )
            return redirect("job_detail", job_id=job.id)
    else:
        form = ReportJobForm()

    return render(
        request,
        "resumes/jobs/report_job.html",
        {
            "form": form,
            "job": job,
        },
    )


@login_required
@job_seeker_required
def generate_cover_letter(request, job_id):
    job = get_object_or_404(
        JobPost,
        id=job_id,
        status=JobPost.STATUS_OPEN,
    )

    if request.method == "POST":
        form = ResumeSelectForm(request.POST, user=request.user)

        if form.is_valid():
            resume = form.cleaned_data["resume"]

            try:
                content = CareerToolsService.generate_cover_letter(resume, job)
            except Exception as exc:
                messages.error(
                    request,
                    "Cover letter generation failed: %s" % exc,
                )
                return redirect("job_detail", job_id=job.id)

            cover_letter = CoverLetter.objects.create(
                user=request.user,
                job=job,
                resume=resume,
                title="Cover Letter - %s" % job.title,
                content=content,
            )

            return redirect(
                "cover_letter_detail",
                cover_letter_id=cover_letter.id,
            )
    else:
        form = ResumeSelectForm(user=request.user)

    return render(
        request,
        "resumes/ai_tools/generate_cover_letter.html",
        {
            "form": form,
            "job": job,
        },
    )


@login_required
@job_seeker_required
def cover_letter_detail(request, cover_letter_id):
    cover_letter = get_object_or_404(
        CoverLetter,
        id=cover_letter_id,
        user=request.user,
    )

    return render(
        request,
        "resumes/ai_tools/cover_letter_detail.html",
        {
            "cover_letter": cover_letter,
        },
    )


@login_required
@job_seeker_required
def cover_letter_history(request):
    cover_letters = CoverLetter.objects.filter(
        user=request.user,
    ).select_related("job", "resume").order_by("-created_at")

    return render(
        request,
        "resumes/ai_tools/cover_letter_history.html",
        {
            "cover_letters": cover_letters,
        },
    )


@login_required
@job_seeker_required
def generate_interview_questions(request, job_id):
    job = get_object_or_404(
        JobPost,
        id=job_id,
        status=JobPost.STATUS_OPEN,
    )

    if request.method == "POST":
        form = ResumeSelectForm(request.POST, user=request.user)

        if form.is_valid():
            resume = form.cleaned_data["resume"]

            try:
                ai_response = CareerToolsService.generate_interview_questions(
                    resume,
                    job,
                )
            except Exception as exc:
                messages.error(
                    request,
                    "Interview questions generation failed: %s" % exc,
                )
                return redirect("job_detail", job_id=job.id)

            question_set = InterviewQuestionSet.objects.create(
                user=request.user,
                job=job,
                resume=resume,
                title="Interview Prep - %s" % job.title,
                ai_response=ai_response,
            )

            return redirect(
                "interview_questions_detail",
                question_set_id=question_set.id,
            )
    else:
        form = ResumeSelectForm(user=request.user)

    return render(
        request,
        "resumes/ai_tools/generate_interview_questions.html",
        {
            "form": form,
            "job": job,
        },
    )


@login_required
@job_seeker_required
def interview_questions_detail(request, question_set_id):
    question_set = get_object_or_404(
        InterviewQuestionSet,
        id=question_set_id,
        user=request.user,
    )

    return render(
        request,
        "resumes/ai_tools/interview_questions_detail.html",
        {
            "question_set": question_set,
        },
    )


@login_required
@job_seeker_required
def interview_questions_history(request):
    question_sets = InterviewQuestionSet.objects.filter(
        user=request.user,
    ).select_related("job", "resume").order_by("-created_at")

    return render(
        request,
        "resumes/ai_tools/interview_questions_history.html",
        {
            "question_sets": question_sets,
        },
    )


@recruiter_required
def recruiter_dashboard(request):
    jobs = JobPost.objects.filter(recruiter=request.user)

    total_jobs = jobs.count()
    open_jobs = jobs.filter(status=JobPost.STATUS_OPEN).count()
    total_applications = JobApplication.objects.filter(
        job__recruiter=request.user,
    ).count()

    recent_applications = JobApplication.objects.filter(
        job__recruiter=request.user,
    ).select_related("job", "applicant", "resume").order_by("-created_at")[:8]

    recent_jobs = jobs.order_by("-created_at")[:5]

    pipeline_counts = {}
    pipeline_chart_labels = []
    pipeline_chart_data = []

    for status_value, status_label in JobApplication.STATUS_CHOICES:
        count = JobApplication.objects.filter(
            job__recruiter=request.user,
            status=status_value,
        ).count()

        pipeline_counts[status_value] = count
        pipeline_chart_labels.append(status_label)
        pipeline_chart_data.append(count)

    job_chart_labels = []
    job_chart_data = []

    for job in jobs.annotate(
        total_applications=Count("applications"),
    ).order_by("-created_at")[:8]:
        job_chart_labels.append(job.title)
        job_chart_data.append(job.total_applications)

    return render(
        request,
        "resumes/recruiter/dashboard.html",
        {
            "total_jobs": total_jobs,
            "open_jobs": open_jobs,
            "total_applications": total_applications,
            "recent_applications": recent_applications,
            "recent_jobs": recent_jobs,
            "pipeline_counts": pipeline_counts,
            "pipeline_chart_labels": pipeline_chart_labels,
            "pipeline_chart_data": pipeline_chart_data,
            "job_chart_labels": job_chart_labels,
            "job_chart_data": job_chart_data,
        },
    )


@recruiter_required
def recruiter_company_profile(request):
    profile = get_or_create_profile(request.user)

    if request.method == "POST":
        form = CompanyProfileForm(
            request.POST,
            request.FILES,
            instance=profile,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Company profile updated successfully.")
            return redirect("recruiter_company_profile")
    else:
        form = CompanyProfileForm(instance=profile)

    return render(
        request,
        "resumes/recruiter/company_profile.html",
        {
            "form": form,
            "profile": profile,
        },
    )


@recruiter_required
def recruiter_candidate_search(request):
    resumes = Resume.objects.filter(
        user__profile__role=Profile.ROLE_JOB_SEEKER,
        user__profile__is_searchable=True,
    ).select_related("user", "user__profile").order_by("-created_at")

    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    skill = request.GET.get("skill", "").strip()
    min_ats = request.GET.get("min_ats", "").strip()

    if q:
        resumes = resumes.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__username__icontains=q)
            | Q(title__icontains=q)
            | Q(summary__icontains=q)
            | Q(target_job_title__icontains=q)
        )

    if location:
        resumes = resumes.filter(user__profile__location__icontains=location)

    if skill:
        resumes = resumes.filter(
            Q(extracted_text__icontains=skill)
            | Q(summary__icontains=skill)
            | Q(target_job_title__icontains=skill)
        )

    if min_ats:
        resumes = resumes.filter(ats_score__gte=min_ats)

    return render(
        request,
        "resumes/recruiter/candidate_search.html",
        {
            "resumes": resumes,
            "q": q,
            "location": location,
            "skill": skill,
            "min_ats": min_ats,
        },
    )


@recruiter_required
def recruiter_candidate_detail(request, user_id):
    User = get_user_model()

    candidate = get_object_or_404(
        User,
        id=user_id,
        profile__role=Profile.ROLE_JOB_SEEKER,
        profile__is_searchable=True,
    )

    resumes = Resume.objects.filter(user=candidate).order_by("-created_at")

    applications = JobApplication.objects.filter(
        applicant=candidate,
        job__recruiter=request.user,
    ).select_related("job").order_by("-created_at")

    return render(
        request,
        "resumes/recruiter/candidate_detail.html",
        {
            "candidate": candidate,
            "resumes": resumes,
            "applications": applications,
        },
    )


@recruiter_required
def recruiter_jobs(request):
    jobs = JobPost.objects.filter(
        recruiter=request.user,
    ).annotate(
        total_applications=Count("applications"),
    ).order_by("-created_at")

    return render(request, "resumes/recruiter/jobs.html", {"jobs": jobs})


@recruiter_required
def recruiter_job_create(request):
    profile = get_or_create_profile(request.user)

    if request.method == "POST":
        form = JobPostForm(request.POST)

        if form.is_valid():
            job = form.save(commit=False)
            job.recruiter = request.user

            if not job.company_name and profile.company_name:
                job.company_name = profile.company_name

            job.save()
            messages.success(request, "Job posted successfully.")
            return redirect("recruiter_jobs")
    else:
        form = JobPostForm(
            initial={
                "company_name": profile.company_name,
                "status": JobPost.STATUS_OPEN,
            },
        )

    return render(
        request,
        "resumes/recruiter/job_form.html",
        {
            "form": form,
            "page_title": "Create Job Post",
            "button_text": "Post Job",
        },
    )


@recruiter_required
def recruiter_job_update(request, job_id):
    job = get_object_or_404(
        JobPost,
        id=job_id,
        recruiter=request.user,
    )

    if request.method == "POST":
        form = JobPostForm(request.POST, instance=job)

        if form.is_valid():
            form.save()
            messages.success(request, "Job updated successfully.")
            return redirect("recruiter_jobs")
    else:
        form = JobPostForm(instance=job)

    return render(
        request,
        "resumes/recruiter/job_form.html",
        {
            "form": form,
            "job": job,
            "page_title": "Edit Job Post",
            "button_text": "Update Job",
        },
    )


@recruiter_required
def recruiter_job_delete(request, job_id):
    job = get_object_or_404(
        JobPost,
        id=job_id,
        recruiter=request.user,
    )

    if request.method == "POST":
        job.delete()
        messages.success(request, "Job deleted successfully.")
        return redirect("recruiter_jobs")

    return render(
        request,
        "resumes/recruiter/job_delete.html",
        {
            "job": job,
        },
    )


@recruiter_required
def recruiter_applications(request):
    applications = JobApplication.objects.filter(
        job__recruiter=request.user,
    ).select_related("job", "applicant", "resume").order_by("-created_at")

    status = request.GET.get("status", "").strip()
    job_id = request.GET.get("job", "").strip()
    q = request.GET.get("q", "").strip()

    if status:
        applications = applications.filter(status=status)

    if job_id:
        applications = applications.filter(job_id=job_id)

    if q:
        applications = applications.filter(
            Q(full_name__icontains=q)
            | Q(email__icontains=q)
            | Q(job__title__icontains=q)
        )

    jobs = JobPost.objects.filter(recruiter=request.user).order_by("-created_at")

    status_counts = {}

    for status_value, status_label in JobApplication.STATUS_CHOICES:
        status_counts[status_value] = JobApplication.objects.filter(
            job__recruiter=request.user,
            status=status_value,
        ).count()

    return render(
        request,
        "resumes/recruiter/applications.html",
        {
            "applications": applications,
            "jobs": jobs,
            "selected_status": status,
            "selected_job": job_id,
            "q": q,
            "status_choices": JobApplication.STATUS_CHOICES,
            "status_counts": status_counts,
        },
    )


@recruiter_required
def recruiter_application_detail(request, application_id):
    application = get_object_or_404(
        JobApplication.objects.select_related("job", "applicant", "resume"),
        id=application_id,
        job__recruiter=request.user,
    )

    old_status = application.status

    if request.method == "POST":
        status = request.POST.get("status")
        recruiter_notes = request.POST.get("recruiter_notes", "")

        valid_statuses = [item[0] for item in JobApplication.STATUS_CHOICES]

        if status in valid_statuses:
            application.status = status

        application.recruiter_notes = recruiter_notes
        application.save()

        if old_status != application.status:
            EmailService.application_status_changed(application)

        messages.success(request, "Application updated successfully.")
        return redirect(
            "recruiter_application_detail",
            application_id=application.id,
        )

    return render(
        request,
        "resumes/recruiter/application_detail.html",
        {
            "application": application,
            "status_choices": JobApplication.STATUS_CHOICES,
        },
    )


@user_passes_test(is_platform_admin)
def platform_admin_dashboard(request):
    total_users = get_user_model().objects.count()
    total_job_seekers = Profile.objects.filter(role=Profile.ROLE_JOB_SEEKER).count()
    total_recruiters = Profile.objects.filter(role=Profile.ROLE_RECRUITER).count()
    pending_recruiters = Profile.objects.filter(
        role=Profile.ROLE_RECRUITER,
        recruiter_status=Profile.RECRUITER_PENDING,
    ).count()
    total_resumes = Resume.objects.count()
    total_jobs = JobPost.objects.count()
    total_applications = JobApplication.objects.count()
    open_reports = ReportedJob.objects.filter(status=ReportedJob.STATUS_OPEN).count()

    recruiter_status_counts = {}

    for value, label in Profile.RECRUITER_STATUS_CHOICES:
        recruiter_status_counts[value] = Profile.objects.filter(
            role=Profile.ROLE_RECRUITER,
            recruiter_status=value,
        ).count()

    application_status_counts = {}

    for value, label in JobApplication.STATUS_CHOICES:
        application_status_counts[value] = JobApplication.objects.filter(
            status=value,
        ).count()

    return render(
        request,
        "resumes/platform_admin/dashboard.html",
        {
            "total_users": total_users,
            "total_job_seekers": total_job_seekers,
            "total_recruiters": total_recruiters,
            "pending_recruiters": pending_recruiters,
            "total_resumes": total_resumes,
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "open_reports": open_reports,
            "recruiter_status_counts": recruiter_status_counts,
            "application_status_counts": application_status_counts,
        },
    )


@user_passes_test(is_platform_admin)
def platform_admin_recruiters(request):
    recruiters = Profile.objects.filter(
        role=Profile.ROLE_RECRUITER,
    ).select_related("user").order_by("-created_at")

    status = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip()

    if status:
        recruiters = recruiters.filter(recruiter_status=status)

    if q:
        recruiters = recruiters.filter(
            Q(company_name__icontains=q)
            | Q(user__username__icontains=q)
            | Q(user__email__icontains=q)
        )

    return render(
        request,
        "resumes/platform_admin/recruiters.html",
        {
            "recruiters": recruiters,
            "status": status,
            "q": q,
            "status_choices": Profile.RECRUITER_STATUS_CHOICES,
        },
    )


@user_passes_test(is_platform_admin)
def platform_admin_update_recruiter_status(request, profile_id):
    profile = get_object_or_404(
        Profile,
        id=profile_id,
        role=Profile.ROLE_RECRUITER,
    )

    if request.method == "POST":
        status = request.POST.get("recruiter_status")
        note = request.POST.get("recruiter_status_note", "")

        valid_statuses = [
            item[0] for item in Profile.RECRUITER_STATUS_CHOICES
        ]

        if status in valid_statuses:
            profile.recruiter_status = status
            profile.recruiter_status_note = note
            profile.save()

            EmailService.recruiter_status_changed(
                recruiter=profile.user,
                status=profile.get_recruiter_status_display(),
                note=note,
            )

            messages.success(
                request,
                "Recruiter status updated and email notification sent."
            )

    return redirect("platform_admin_recruiters")


@user_passes_test(is_platform_admin)
def platform_admin_reported_jobs(request):
    reports = ReportedJob.objects.select_related(
        "job",
        "reporter",
    ).order_by("-created_at")

    status = request.GET.get("status", "").strip()

    if status:
        reports = reports.filter(status=status)

    return render(
        request,
        "resumes/platform_admin/reported_jobs.html",
        {
            "reports": reports,
            "status": status,
            "status_choices": ReportedJob.STATUS_CHOICES,
        },
    )


@user_passes_test(is_platform_admin)
def platform_admin_update_report_status(request, report_id):
    report = get_object_or_404(ReportedJob, id=report_id)

    if request.method == "POST":
        status = request.POST.get("status")
        admin_notes = request.POST.get("admin_notes", "")

        valid_statuses = [item[0] for item in ReportedJob.STATUS_CHOICES]

        if status in valid_statuses:
            report.status = status
            report.admin_notes = admin_notes
            report.save()

            messages.success(request, "Report updated successfully.")

    return redirect("platform_admin_reported_jobs")



# for ai chatbot integration #

@login_required
def chatbot_page(request):
    sessions = ChatSession.objects.filter(
        user=request.user
    ).order_by("-updated_at")

    active_session = sessions.first()

    if not active_session:
        active_session = ChatSession.objects.create(
            user=request.user,
            title="New Chat",
        )

    messages_list = active_session.messages.all()

    return render(
        request,
        "resumes/chatbot.html",
        {
            "sessions": sessions,
            "active_session": active_session,
            "messages_list": messages_list,
        },
    )


@login_required
def chatbot_new_session(request):
    session = ChatSession.objects.create(
        user=request.user,
        title="New Chat",
    )

    return redirect("chatbot_session", session_id=session.id)


@login_required
def chatbot_session(request, session_id):
    sessions = ChatSession.objects.filter(
        user=request.user
    ).order_by("-updated_at")

    active_session = get_object_or_404(
        ChatSession,
        id=session_id,
        user=request.user,
    )

    messages_list = active_session.messages.all()

    return render(
        request,
        "resumes/chatbot.html",
        {
            "sessions": sessions,
            "active_session": active_session,
            "messages_list": messages_list,
        },
    )


@login_required
@require_POST
def chatbot_send_message(request, session_id):
    session = get_object_or_404(
        ChatSession,
        id=session_id,
        user=request.user,
    )

    user_message = request.POST.get("message", "").strip()

    if not user_message:
        return JsonResponse(
            {
                "success": False,
                "error": "Message is required.",
            },
            status=400,
        )

    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_USER,
        content=user_message,
    )

    if session.title == "New Chat":
        session.title = user_message[:60]
        session.save(update_fields=["title", "updated_at"])

    try:
        assistant_reply = ChatbotService.ask(
            user=request.user,
            session=session,
            user_message=user_message,
        )

    except Exception as exc:
        assistant_reply = "Sorry, AI chatbot failed to respond. Error: %s" % exc

    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_ASSISTANT,
        content=assistant_reply,
    )

    session.save(update_fields=["updated_at"])

    return JsonResponse(
        {
            "success": True,
            "reply": assistant_reply,
        }
    )


# for ai agent integration #

@login_required
def ai_agent_page(request):
    sessions = AgentSession.objects.filter(
        user=request.user
    ).order_by("-updated_at")

    active_session = sessions.first()

    if not active_session:
        active_session = AgentSession.objects.create(
            user=request.user,
            title="New Agent Chat",
        )

    messages_list = active_session.messages.all()

    return render(
        request,
        "resumes/agent.html",
        {
            "sessions": sessions,
            "active_session": active_session,
            "messages_list": messages_list,
        },
    )


@login_required
def ai_agent_new_session(request):
    session = AgentSession.objects.create(
        user=request.user,
        title="New Agent Chat",
    )

    return redirect("ai_agent_session", session_id=session.id)


@login_required
def ai_agent_session(request, session_id):
    sessions = AgentSession.objects.filter(
        user=request.user
    ).order_by("-updated_at")

    active_session = get_object_or_404(
        AgentSession,
        id=session_id,
        user=request.user,
    )

    messages_list = active_session.messages.all()

    return render(
        request,
        "resumes/agent.html",
        {
            "sessions": sessions,
            "active_session": active_session,
            "messages_list": messages_list,
        },
    )


@login_required
@require_POST
def ai_agent_send_message(request, session_id):
    session = get_object_or_404(
        AgentSession,
        id=session_id,
        user=request.user,
    )

    user_message = request.POST.get("message", "").strip()

    if not user_message:
        return JsonResponse(
            {
                "success": False,
                "error": "Message is required.",
            },
            status=400,
        )

    AgentMessage.objects.create(
        session=session,
        role=AgentMessage.ROLE_USER,
        content=user_message,
    )

    if session.title == "New Agent Chat":
        session.title = user_message[:60]
        session.save(update_fields=["title", "updated_at"])

    try:
        result = RecruitmentAgentService.run_agent(
            user=request.user,
            session=session,
            user_message=user_message,
        )

        answer = result["answer"]
        tool_name = result["tool_name"]
        tool_result = result["tool_result"]

    except Exception as exc:
        answer = "AI agent failed: %s" % exc
        tool_name = ""
        tool_result = {
            "success": False,
            "error": str(exc),
        }

    AgentMessage.objects.create(
        session=session,
        role=AgentMessage.ROLE_AGENT,
        content=answer,
        tool_name=tool_name,
        tool_result=tool_result,
    )

    session.save(update_fields=["updated_at"])

    return JsonResponse(
        {
            "success": True,
            "reply": answer,
            "tool_name": tool_name,
            "tool_result": tool_result,
        }
    )


@login_required
@require_POST
def ai_agent_confirm_action(request, action_id):
    action = get_object_or_404(
        AgentActionLog,
        id=action_id,
        user=request.user,
        status=AgentActionLog.STATUS_PROPOSED,
    )

    if action.action_name == "shortlist_candidate":
        application_id = action.input_data.get("application_id")

        try:
            application = JobApplication.objects.get(
                id=application_id,
                job__recruiter=request.user,
            )

            application.status = JobApplication.STATUS_SHORTLISTED
            application.save(update_fields=["status", "updated_at"])

            action.status = AgentActionLog.STATUS_COMPLETED
            action.result_data = {
                "message": "Candidate shortlisted successfully.",
                "application_id": application.id,
            }
            action.save(update_fields=["status", "result_data", "updated_at"])

            return JsonResponse(
                {
                    "success": True,
                    "message": "Candidate shortlisted successfully.",
                }
            )

        except Exception as exc:
            action.status = AgentActionLog.STATUS_FAILED
            action.result_data = {
                "error": str(exc),
            }
            action.save(update_fields=["status", "result_data", "updated_at"])

            return JsonResponse(
                {
                    "success": False,
                    "error": str(exc),
                },
                status=400,
            )

    return JsonResponse(
        {
            "success": False,
            "error": "Unsupported action.",
        },
        status=400,
    )
    

@login_required
def ai_agent_widget_bootstrap(request):
    session = AgentSession.objects.filter(
        user=request.user
    ).order_by("-updated_at").first()

    if not session:
        session = AgentSession.objects.create(
            user=request.user,
            title="Floating AI Agent",
        )

    messages = session.messages.order_by("-created_at")[:10]
    messages = reversed(list(messages))

    messages_data = []

    for message in messages:
        messages_data.append(
            {
                "role": message.role,
                "content": message.content,
                "tool_name": message.tool_name,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "session_id": session.id,
            "messages": messages_data,
        }
    )


@login_required
@require_POST
def ai_agent_widget_send(request):
    session_id = request.POST.get("session_id")
    user_message = request.POST.get("message", "").strip()

    if not user_message:
        return JsonResponse(
            {
                "success": False,
                "error": "Message is required.",
            },
            status=400,
        )

    session = None

    if session_id:
        session = AgentSession.objects.filter(
            id=session_id,
            user=request.user,
        ).first()

    if not session:
        session = AgentSession.objects.create(
            user=request.user,
            title="Floating AI Agent",
        )

    AgentMessage.objects.create(
        session=session,
        role=AgentMessage.ROLE_USER,
        content=user_message,
    )

    if session.title in ["New Agent Chat", "Floating AI Agent"]:
        session.title = user_message[:60]
        session.save(update_fields=["title", "updated_at"])

    try:
        result = RecruitmentAgentService.run_agent(
            user=request.user,
            session=session,
            user_message=user_message,
        )

        answer = result["answer"]
        tool_name = result["tool_name"]
        tool_result = result["tool_result"]

    except Exception as exc:
        answer = "AI agent failed: %s" % exc
        tool_name = ""
        tool_result = {
            "success": False,
            "error": str(exc),
        }

    AgentMessage.objects.create(
        session=session,
        role=AgentMessage.ROLE_AGENT,
        content=answer,
        tool_name=tool_name,
        tool_result=tool_result,
    )

    session.save(update_fields=["updated_at"])

    return JsonResponse(
        {
            "success": True,
            "session_id": session.id,
            "reply": answer,
            "tool_name": tool_name,
        }
    )    
    

@login_required
@require_POST
def ai_agent_clear_all_chats(request):
    AgentSession.objects.filter(
        user=request.user
    ).delete()

    messages.success(
        request,
        "All AI Agent chats cleared successfully."
    )

    return redirect("ai_agent_page")    
    

@login_required
@require_POST
def ai_agent_widget_new_session(request):
    session = AgentSession.objects.create(
        user=request.user,
        title="Floating AI Agent",
    )

    return JsonResponse({
        "success": True,
        "session_id": session.id,
        "message": "New chat started.",
    })


@login_required
@require_POST
def ai_agent_widget_clear_all_chats(request):
    AgentSession.objects.filter(
        user=request.user
    ).delete()

    session = AgentSession.objects.create(
        user=request.user,
        title="Floating AI Agent",
    )

    return JsonResponse({
        "success": True,
        "session_id": session.id,
        "message": "All AI Agent chats cleared.",
    })

   