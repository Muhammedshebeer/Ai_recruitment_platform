from resumes.services.prompt_service import PromptService

text = """
Muhammed Shabeer

Python
Django
FastAPI
PostgreSQL
"""

prompt = PromptService.resume_analysis_prompt(text)

print(prompt)