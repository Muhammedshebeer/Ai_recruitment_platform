from .rag_service import RAGService


class RAGSyncService:

    @classmethod
    def index_resume(cls, resume):
        text = """
Record Type: Resume

Resume ID: {resume_id}
Owner ID: {owner_id}
Owner Username: {username}

Resume Title: {title}
Target Job Title: {target_job_title}
Target Location: {target_location}
ATS Score: {ats_score}
Job Match Score: {job_match_score}

Summary:
{summary}

Skills:
{skills}

Missing Skills:
{missing_skills}

Things To Add:
{things_to_add}

Keywords To Add:
{keywords_to_add}

Extracted Resume Text:
{extracted_text}
""".format(
            resume_id=resume.id,
            owner_id=resume.user_id,
            username=resume.user.username if resume.user else "",
            title=resume.title,
            target_job_title=resume.target_job_title,
            target_location=resume.target_location,
            ats_score=resume.ats_score or 0,
            job_match_score=resume.job_match_score or 0,
            summary=resume.summary or "",
            skills=", ".join(resume.skills or []),
            missing_skills=", ".join(resume.missing_skills or []),
            things_to_add=", ".join(resume.things_to_add or []),
            keywords_to_add=", ".join(resume.keywords_to_add or []),
            extracted_text=resume.extracted_text or "",
        )

        return RAGService.upsert_record(
            record_type="resume",
            record_id=resume.id,
            text=text,
            metadata={
                "owner_id": resume.user_id,
                "title": resume.title,
                "ats_score": resume.ats_score or 0,
                "target_job_title": resume.target_job_title,
            },
        )

    @classmethod
    def index_job_post(cls, job):
        text = """
Record Type: Job Post

Job ID: {job_id}
Recruiter ID: {recruiter_id}
Job Title: {title}
Company Name: {company_name}
Location: {location}
Job Type: {job_type}
Status: {status}
Salary Min: {salary_min}
Salary Max: {salary_max}
Deadline: {deadline}

Description:
{description}

Requirements:
{requirements}

Responsibilities:
{responsibilities}

Skills Required:
{skills_required}
""".format(
            job_id=job.id,
            recruiter_id=job.recruiter_id,
            title=job.title,
            company_name=job.company_name,
            location=job.location,
            job_type=job.get_job_type_display(),
            status=job.status,
            salary_min=job.salary_min or "",
            salary_max=job.salary_max or "",
            deadline=job.deadline or "",
            description=job.description or "",
            requirements=job.requirements or "",
            responsibilities=job.responsibilities or "",
            skills_required=", ".join(job.skills_required or []),
        )

        record_type = "job_post"

        if job.recruiter_id:
            record_type = "recruiter_job"

        return RAGService.upsert_record(
            record_type=record_type,
            record_id=job.id,
            text=text,
            metadata={
                "job_id": job.id,
                "recruiter_id": job.recruiter_id,
                "title": job.title,
                "company_name": job.company_name,
                "location": job.location,
                "status": job.status,
            },
        )

    @classmethod
    def index_job_application(cls, application):
        job = application.job
        resume = application.resume

        text = """
Record Type: Job Application

Application ID: {application_id}
Applicant ID: {applicant_id}
Applicant Name: {applicant_name}
Applicant Email: {email}

Job ID: {job_id}
Job Recruiter ID: {job_recruiter_id}
Job Title: {job_title}
Company Name: {company_name}
Location: {location}

Application Status: {status}
Match Score: {match_score}
Applied Date: {applied_date}

Resume Used: {resume_title}
Cover Letter:
{cover_letter}
""".format(
            application_id=application.id,
            applicant_id=application.applicant_id,
            applicant_name=application.full_name,
            email=application.email,
            job_id=job.id,
            job_recruiter_id=job.recruiter_id,
            job_title=job.title,
            company_name=job.company_name,
            location=job.location,
            status=application.get_status_display(),
            match_score=application.match_score or 0,
            applied_date=application.created_at.strftime("%Y-%m-%d %H:%M"),
            resume_title=resume.title if resume else "",
            cover_letter=application.cover_letter or "",
        )

        return RAGService.upsert_record(
            record_type="job_application",
            record_id=application.id,
            text=text,
            metadata={
                "application_id": application.id,
                "applicant_id": application.applicant_id,
                "job_id": job.id,
                "job_recruiter_id": job.recruiter_id,
                "job_title": job.title,
                "company_name": job.company_name,
                "status": application.status,
                "applied_date": application.created_at.date().isoformat(),
            },
        )

    @classmethod
    def index_company_profile(cls, profile):
        text = """
Record Type: Company Profile

Profile ID: {profile_id}
Recruiter User ID: {user_id}
Company Name: {company_name}
Company Location: {company_location}
Company Website: {company_website}
Phone: {phone}
Recruiter Status: {recruiter_status}

Company About:
{company_about}
""".format(
            profile_id=profile.id,
            user_id=profile.user_id,
            company_name=profile.company_name,
            company_location=profile.company_location,
            company_website=profile.company_website,
            phone=profile.phone,
            recruiter_status=profile.recruiter_status,
            company_about=profile.company_about or "",
        )

        return RAGService.upsert_record(
            record_type="company_profile",
            record_id=profile.id,
            text=text,
            metadata={
                "profile_id": profile.id,
                "user_id": profile.user_id,
                "company_name": profile.company_name,
                "recruiter_status": profile.recruiter_status,
            },
        )