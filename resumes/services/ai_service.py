import json

from django.conf import settings
from openai import OpenAI


class AIService:

    @staticmethod
    def get_client():
        if not getattr(settings, "OPENAI_API_KEY", None):
            raise ValueError(
                "OPENAI_API_KEY is missing. Add it to your .env file and settings.py."
            )

        return OpenAI(
            api_key=settings.OPENAI_API_KEY,
        )

    @classmethod
    def ask(cls, prompt):
        """
        Used for resume ATS analysis.
        Returns Python dict.
        """

        client = cls.get_client()

        response = client.responses.create(
    model=settings.OPENAI_MODEL,
    input=[
        {
            "role": "system",
            "content": (
                "You are an ATS resume analyzer for an AI recruitment platform. "
                "Return only valid compact JSON matching the schema. "
                "Do not explain. Do not use markdown. Do not add extra keys. "
                "Keep all string fields short. Each array must contain maximum 5 items."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ],
    reasoning={
        "effort": "minimal",
    },
    text={
        "format": {
            "type": "json_schema",
            "name": "resume_analysis_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "ats_score": {"type": "integer"},
                    "job_match_score": {"type": "integer"},
                    "summary": {"type": "string"},
                    "improved_summary": {"type": "string"},
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "missing_skills": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "strengths": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "weak_sections": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "improvements": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "things_to_add": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "resume_bullet_points": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "keywords_to_add": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "job_match_feedback": {"type": "string"},
                },
                "required": [
                    "ats_score",
                    "job_match_score",
                    "summary",
                    "improved_summary",
                    "skills",
                    "missing_skills",
                    "strengths",
                    "weak_sections",
                    "improvements",
                    "things_to_add",
                    "resume_bullet_points",
                    "keywords_to_add",
                    "job_match_feedback",
                ],
                "additionalProperties": False,
            },
        }
    },
    max_output_tokens=4000,
)

        output_text = getattr(response, "output_text", "")

        if not output_text:
            print("OPENAI RAW RESPONSE:")
            print(response.model_dump_json(indent=2))

            raise ValueError(
                "OpenAI returned empty output_text. Check raw response printed above."
            )

        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            print("OPENAI OUTPUT TEXT:")
            print(output_text)

            print("OPENAI RAW RESPONSE:")
            print(response.model_dump_json(indent=2))

            raise ValueError("OpenAI returned text, but it was not valid JSON.")

    @classmethod
    def ask_text(cls, messages, max_output_tokens=1000):
        """
        Used for chatbot / AI agent normal replies.
        Returns plain text.
        """

        client = cls.get_client()

        response = client.responses.create(
    model=settings.OPENAI_MODEL,
    input=messages,
    reasoning={
        "effort": "minimal",
    },
    max_output_tokens=max_output_tokens,
)

        output_text = getattr(response, "output_text", "")

        if not output_text:
            print("OPENAI RAW RESPONSE:")
            print(response.model_dump_json(indent=2))

            raise ValueError(
                "OpenAI returned empty output_text. Check raw response printed above."
            )

        return output_text.strip()

    @classmethod
    def ask_json(
        cls,
        messages,
        schema,
        schema_name="ai_json_response",
        max_output_tokens=1000,
    ):
        """
        Used for AI agent tool decisions.
        Returns Python dict.
        """

        client = cls.get_client()

        response = client.responses.create(
    model=settings.OPENAI_MODEL,
    input=messages,
    reasoning={
        "effort": "minimal",
    },
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
            max_output_tokens=max_output_tokens,
        )

        output_text = getattr(response, "output_text", "")

        if not output_text:
            print("OPENAI RAW RESPONSE:")
            print(response.model_dump_json(indent=2))

            raise ValueError(
                "OpenAI returned empty output_text. Check raw response printed above."
            )

        try:
            return json.loads(output_text)
        except json.JSONDecodeError:
            print("OPENAI OUTPUT TEXT:")
            print(output_text)

            print("OPENAI RAW RESPONSE:")
            print(response.model_dump_json(indent=2))

            raise ValueError("OpenAI returned text, but it was not valid JSON.")