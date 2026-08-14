import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


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

        except Exception as exc:
            logger.exception("Email sending failed: %s", exc)
            return False

    @classmethod
    def recruiter_pending_notice(cls, recruiter):
        try:
            profile = getattr(recruiter, "profile", None)

            company_name = ""
            phone = ""
            company_document_type = ""

            if profile:
                company_name = getattr(profile, "company_name", "") or ""
                phone = getattr(profile, "phone", "") or ""
                company_document_type = getattr(profile, "company_document_type", "") or ""

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
                    company_name,
                    phone,
                    company_document_type,
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

        except Exception as exc:
            logger.exception("Recruiter pending notice failed: %s", exc)
            return False

        return True

    @classmethod
    def recruiter_status_changed(cls, recruiter, status, note=""):
        try:
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

        except Exception as exc:
            logger.exception("Recruiter status email failed: %s", exc)
            return False

        return True