from resumes.services.ai_service import AIService

response = AIService.ask(
    "What is Django?"
)

print(response)