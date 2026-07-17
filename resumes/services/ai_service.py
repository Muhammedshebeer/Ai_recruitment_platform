import json
import re
import requests


class AIService:
    OLLAMA_URL = "http://localhost:11434/api/chat"
    MODEL = "qwen3"

    @classmethod
    def ask(cls, prompt):
        payload = {
            "model": cls.MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_predict": 900,
                "num_ctx": 4096,
            },
        }

        response = requests.post(cls.OLLAMA_URL, json=payload, timeout=600)
        response.raise_for_status()

        result = response.json()
        content = result.get("message", {}).get("content", "")

        return cls.parse_json_response(content)

    @staticmethod
    def parse_json_response(content):
        if not content:
            raise ValueError("Empty response received from Ollama.")

        text = content.strip()
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

        if text.startswith("```json"):
            text = text.replace("```json", "", 1).strip()

        if text.startswith("```"):
            text = text.replace("```", "", 1).strip()

        if text.endswith("```"):
            text = text[:-3].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)

        if not match:
            raise ValueError("Ollama did not return valid JSON. Response was: %s" % text[:500])

        return json.loads(match.group(0))
