from resumes.services.pdf_service import PDFService

text = PDFService.extract_text(
    "media/resumes/muhd_shabeer_Resume.pdf"
)

print(text)