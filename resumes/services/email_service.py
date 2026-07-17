from django.conf import settings
from django.core.mail import send_mail


class EmailService:

    @staticmethod
    def send(subject, message, recipients):
        recipients = [email for email in recipients if email]

        if not recipients:
            return False

        from_email = getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            "noreply@example.com",
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipients,
                fail_silently=True,
            )
            return True

        except Exception:
            return False

    @classmethod
    def recruiter_pending_notice(cls, recruiter):
        profile = recruiter.profile

        admin_email = getattr(settings, "ADMIN_EMAIL", None)

        cls.send(
            subject="New recruiter pending approval",
            message=(
                "A new recruiter has registered and is pending approval.\n\n"
                "Username: %s\n"
                "Email: %s\n"
                "Company: %s\n"
                "Phone: %s\n"
                "Document Type: %s\n\n"
                "Please login to the platform admin dashboard to review this recruiter."
            ) % (
                recruiter.username,
                recruiter.email,
                profile.company_name,
                profile.phone,
                profile.company_document_type,
            ),
            recipients=[admin_email],
        )

        cls.send(
            subject="Recruiter account submitted for approval",
            message=(
                "Dear %s,\n\n"
                "Your recruiter account has been submitted successfully.\n"
                "Our admin team will review your company details and documents.\n\n"
                "You will receive another email once your account is approved.\n\n"
                "Thank you."
            ) % (recruiter.get_full_name() or recruiter.username),
            recipients=[recruiter.email],
        )

    @classmethod
    def recruiter_status_changed(cls, recruiter, status, note=""):
        cls.send(
            subject="Recruiter account status updated",
            message=(
                "Dear %s,\n\n"
                "Your recruiter account status has been updated.\n\n"
                "Current Status: %s\n\n"
                "%s\n\n"
                "Thank you."
            ) % (
                recruiter.get_full_name() or recruiter.username,
                status,
                note or "",
            ),
            recipients=[recruiter.email],
        )