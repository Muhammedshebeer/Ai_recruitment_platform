from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import JobApplication, JobPost, Profile, Resume,ReportedJob
from .services.job_matching_services import JobMatchingService


COMMON_INPUT_CLASS = "w-full rounded-xl bg-slate-900 border border-slate-700 px-5 py-4 outline-none focus:border-blue-500"
COMMON_TEXTAREA_CLASS = "w-full rounded-xl bg-slate-900 border border-slate-700 px-5 py-4 outline-none focus:border-blue-500 min-h-[150px]"


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = [
            "title",
            "target_job_title",
            "target_experience_level",
            "target_location",
            "target_job_description",
            "pdf",
        ]

        widgets = {
            "title": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Example: Backend Developer Resume"}),
            "target_job_title": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Target job title, example: Django Developer"}),
            "target_experience_level": forms.Select(attrs={"class": COMMON_INPUT_CLASS}),
            "target_location": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Preferred location, example: Dubai / Remote"}),
            "target_job_description": forms.Textarea(attrs={"class": COMMON_TEXTAREA_CLASS, "placeholder": "Paste the job description here for accurate ATS keywords, missing skills, and bullet points.", "rows": 7}),
            "pdf": forms.ClearableFileInput(attrs={"class": "hidden", "accept": ".pdf,application/pdf"}),
        }

    def clean_pdf(self):
        pdf = self.cleaned_data.get("pdf")

        if pdf:
            file_name = pdf.name.lower()

            if not file_name.endswith(".pdf"):
                raise forms.ValidationError("Only PDF files are allowed.")

            if pdf.size > 10 * 1024 * 1024:
                raise forms.ValidationError("PDF file must be 10 MB or less.")

        return pdf


class RegisterForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "First name"}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Last name"}))
    username = forms.CharField(widget=forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Username"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Email address"}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Password"}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Confirm password"}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered.")

        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")

        if commit:
            user.save()
            Profile.objects.get_or_create(user=user, defaults={"role": Profile.ROLE_JOB_SEEKER})

        return user


class RecruiterRegisterForm(RegisterForm):

    company_name = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": COMMON_INPUT_CLASS,
                "placeholder": "Company name",
            }
        ),
    )

    phone = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": COMMON_INPUT_CLASS,
                "placeholder": "Phone number",
            }
        ),
    )

    company_document_type = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": COMMON_INPUT_CLASS,
                "placeholder": "Example: Trade License / Company Registration",
            }
        ),
    )

    company_document = forms.FileField(
        required=True,
        widget=forms.ClearableFileInput(
            attrs={
                "class": COMMON_INPUT_CLASS,
                "accept": ".pdf,.jpg,.jpeg,.png",
            }
        ),
    )

    class Meta(RegisterForm.Meta):
        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "company_name",
            "phone",
            "company_document_type",
            "company_document",
            "password1",
            "password2",
        ]

    def clean_company_document(self):
        document = self.cleaned_data.get("company_document")

        if document:
            allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]
            file_name = document.name.lower()

            if not any(file_name.endswith(ext) for ext in allowed_extensions):
                raise forms.ValidationError(
                    "Only PDF, JPG, JPEG, or PNG files are allowed."
                )

            if document.size > 10 * 1024 * 1024:
                raise forms.ValidationError(
                    "Company document must be 10 MB or less."
                )

        return document

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")

        if commit:
            user.save()

            Profile.objects.update_or_create(
                user=user,
                defaults={
                    "role": Profile.ROLE_RECRUITER,
                    "company_name": self.cleaned_data.get("company_name", ""),
                    "phone": self.cleaned_data.get("phone", ""),
                    "company_document_type": self.cleaned_data.get("company_document_type", ""),
                    "company_document": self.cleaned_data.get("company_document"),
                    "recruiter_status": Profile.RECRUITER_PENDING,
                },
            )

        return user

class JobPostForm(forms.ModelForm):
    skills_required_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": COMMON_TEXTAREA_CLASS, "placeholder": "Example: Python, Django, REST API, PostgreSQL, Docker", "rows": 4}),
        help_text="Enter skills separated by commas or new lines.",
    )

    class Meta:
        model = JobPost
        fields = [
            "title",
            "company_name",
            "location",
            "job_type",
            "description",
            "requirements",
            "responsibilities",
            "salary_min",
            "salary_max",
            "status",
            "deadline",
        ]

        widgets = {
            "title": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Job title"}),
            "company_name": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Company name"}),
            "location": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Dubai, UAE / Remote"}),
            "job_type": forms.Select(attrs={"class": COMMON_INPUT_CLASS}),
            "description": forms.Textarea(attrs={"class": COMMON_TEXTAREA_CLASS, "placeholder": "Describe the role"}),
            "requirements": forms.Textarea(attrs={"class": COMMON_TEXTAREA_CLASS, "placeholder": "Candidate requirements"}),
            "responsibilities": forms.Textarea(attrs={"class": COMMON_TEXTAREA_CLASS, "placeholder": "Main responsibilities"}),
            "salary_min": forms.NumberInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Minimum salary"}),
            "salary_max": forms.NumberInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Maximum salary"}),
            "status": forms.Select(attrs={"class": COMMON_INPUT_CLASS}),
            "deadline": forms.DateInput(attrs={"class": COMMON_INPUT_CLASS, "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["skills_required_text"].initial = ", ".join(self.instance.skills_required or [])

    def clean_skills_required_text(self):
        value = self.cleaned_data.get("skills_required_text", "")
        skills = []

        for item in value.replace("\n", ",").split(","):
            item = item.strip()

            if item:
                skills.append(item)

        return skills

    def save(self, commit=True):
        job = super().save(commit=False)
        job.skills_required = self.cleaned_data.get("skills_required_text", [])

        if commit:
            job.save()

        return job


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ["resume", "full_name", "email", "phone", "cover_letter"]

        widgets = {
            "resume": forms.Select(attrs={"class": COMMON_INPUT_CLASS}),
            "full_name": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Email address"}),
            "phone": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Phone number"}),
            "cover_letter": forms.Textarea(attrs={"class": COMMON_TEXTAREA_CLASS, "placeholder": "Short cover letter"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        job = kwargs.pop("job", None)

        super().__init__(*args, **kwargs)

        if user:
            resumes = Resume.objects.filter(user=user).order_by("-created_at")
            self.fields["resume"].queryset = resumes

            if job:
                

                choices = []
                for resume in resumes:
                    score = JobMatchingService.calculate_match_score(resume, job)
                    choices.append((resume.id, "%s - %s%% match" % (resume.title, score)))

                self.fields["resume"].choices = choices

            full_name = user.get_full_name() or user.username
            self.fields["full_name"].initial = full_name
            self.fields["email"].initial = user.email
        else:
            self.fields["resume"].queryset = Resume.objects.none()


class ResumeSelectForm(forms.Form):
    resume = forms.ModelChoiceField(
        queryset=Resume.objects.none(),
        widget=forms.Select(attrs={"class": COMMON_INPUT_CLASS}),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields["resume"].queryset = Resume.objects.filter(user=user).order_by("-created_at")



# PHASE 3: Add these imports in forms.py
# from .models import ReportedJob

class CandidateProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "headline",
            "location",
            "about",
            "linkedin_url",
            "portfolio_url",
            "is_searchable",
        ]

        widgets = {
            "headline": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Example: Django Backend Developer"}),
            "location": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Dubai, UAE"}),
            "about": forms.Textarea(attrs={"class": COMMON_TEXTAREA_CLASS, "placeholder": "Short candidate profile"}),
            "linkedin_url": forms.URLInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "LinkedIn URL"}),
            "portfolio_url": forms.URLInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Portfolio / GitHub URL"}),
            "is_searchable": forms.CheckboxInput(attrs={"class": "w-5 h-5"}),
        }


class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "company_name",
            "company_about",
            "company_website",
            "company_location",
            "company_logo",
            "phone",
        ]

        widgets = {
            "company_name": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Company name"}),
            "company_about": forms.Textarea(attrs={"class": COMMON_TEXTAREA_CLASS, "placeholder": "About your company"}),
            "company_website": forms.URLInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "https://example.com"}),
            "company_location": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Dubai, UAE"}),
            "company_logo": forms.ClearableFileInput(attrs={"class": COMMON_INPUT_CLASS}),
            "phone": forms.TextInput(attrs={"class": COMMON_INPUT_CLASS, "placeholder": "Phone number"}),
        }


class ReportJobForm(forms.ModelForm):
    class Meta:
        model = ReportedJob
        fields = ["reason", "details"]

        widgets = {
            "reason": forms.Select(attrs={"class": COMMON_INPUT_CLASS}),
            "details": forms.Textarea(attrs={"class": COMMON_TEXTAREA_CLASS, "placeholder": "Explain the issue with this job post"}),
        }
