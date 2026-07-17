from resumes.services.ai_service import AIService
from resumes.services.prompt_service import PromptService
from resumes.services.pdf_service import PDFService

resume_text = PDFService.extract_text(
    "media/resumes/muhd_shabeer_Resume.pdf"
)

prompt = PromptService.resume_analysis_prompt(resume_text)

response = AIService.ask(prompt)

print(type(response))
print(response)