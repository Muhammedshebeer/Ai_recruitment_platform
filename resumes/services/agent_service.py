import json
import re
import requests

from django.conf import settings

from .agent_tools import RecruitmentAgentTools
from .ai_service import AIService


class RecruitmentAgentService:

    @staticmethod
    def parse_json(text):
        if not text:
            return {}

        text = text.strip()

        text = re.sub(
            r"<think>.*?</think>",
            "",
            text,
            flags=re.DOTALL | re.IGNORECASE,
        ).strip()

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

        if match:
            return json.loads(match.group(0))

        return {}

    @staticmethod
    def call_ai(messages, json_mode=False):
        if json_mode:
            schema = {
                "type": "object",
                "properties": {
                    "tool": {
                        "type": "string"
                    },
                    "arguments_json": {
                        "type": "string"
                    },
                    "reason": {
                        "type": "string"
                    },
                },
                "required": [
                    "tool",
                    "arguments_json",
                    "reason",
                ],
                "additionalProperties": False,
            }

            return AIService.ask_json(
                messages=messages,
                schema=schema,
                schema_name="agent_tool_decision",
                max_output_tokens=1000,
            )

        return AIService.ask_text(
            messages=messages,
            max_output_tokens=1200,
        )

    @classmethod
    def decide_tool(cls, user, session, user_message):
        role = RecruitmentAgentTools.get_user_role(user)

        system_prompt = """
You are a tool-selecting AI agent inside a recruitment platform.

Your job is to select the best tool for the user's request.

Return ONLY valid JSON.

Available tools:

1. latest_resume_summary
Use when job seeker asks about resume score, ATS score, skills, missing skills, resume improvement.

2. suggest_jobs_for_user
Use when job seeker asks for matching jobs, best jobs, jobs to apply for.

3. my_applications
Use when job seeker asks about their applications or application status.

4. recruiter_jobs
Use when recruiter asks about their jobs, job posts, job performance.

5. rank_candidates_for_job
Use when recruiter asks to rank candidates for a specific job.
Requires: job_id.

6. platform_summary
Use when admin asks about platform statistics.

7. propose_shortlist_candidate
Use only when recruiter asks to shortlist a candidate.
Requires: application_id.
This tool only proposes action and needs confirmation.

If no tool fits, return:
{
    "tool": "none",
    "arguments": {},
    "reason": "Explain briefly"
}

Current user role:
%s

Return JSON structure:
{
    "tool": "",
    "arguments": {},
    "reason": ""
}
8. rag_search_platform_knowledge
Use this when the user asks any question that needs searching platform knowledge, resumes, jobs, applications, companies, candidate information, or previous records.

Arguments:
{
    "query": "the user's search question",
    "top_k": 8
}

Examples:
User: "list the jobs I applied yesterday"
Return:
{
    "tool": "rag_search_platform_knowledge",
    "arguments": {
        "query": "jobs I applied yesterday",
        "top_k": 8
    },
    "reason": "User is asking for application records from platform knowledge."
}

User: "which jobs match my resume?"
Return:
{
    "tool": "rag_search_platform_knowledge",
    "arguments": {
        "query": "jobs matching my resume skills and target job title",
        "top_k": 8
    },
    "reason": "User is asking for platform knowledge using RAG."
}
""" % role

        recent_messages = session.messages.order_by("-created_at")[:6]
        recent_messages = reversed(list(recent_messages))

        conversation_text = ""

        for message in recent_messages:
            conversation_text += "%s: %s\n" % (
                message.role,
                message.content,
            )

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    "Conversation history:\n%s\n\nCurrent user message:\n%s"
                    % (
                        conversation_text,
                        user_message,
                    )
                ),
            },
        ]

        data = cls.call_ai(
    messages=messages,
    json_mode=True,
)
        
        arguments_json = data.get("arguments_json", "{}")

        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError:
            arguments = {}

        return {
            "tool": data.get("tool", "none"),
            "arguments": arguments,
            "reason": data.get("reason", ""),
        }

    @classmethod
    def final_answer(cls, user, user_message, tool_name, tool_result):
        role = RecruitmentAgentTools.get_user_role(user)

        system_prompt = """
You are a recruitment AI agent inside a Django AI recruitment platform.

User role: %s

Answer clearly and practically.

Rules:
- Use only the provided tool result as your source.
- If the tool result source is rag_vector_database, say the answer is based on indexed platform knowledge.
- Do not invent records.
- Do not reveal records the user is not allowed to access.
- If no relevant RAG results are found, say no matching indexed knowledge was found.
- If results contain job applications, list job title, company, status, match score, and applied date if available.
- If results contain jobs, list job title, company, location, job type, and status if available.
- For recruiters, be direct and decision-focused.
- For job seekers, be practical and clear.
""" % role

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    "User asked:\n%s\n\n"
                    "Tool used:\n%s\n\n"
                    "Tool result:\n%s"
                ) % (
                    user_message,
                    tool_name,
                    json.dumps(tool_result, indent=2),
                ),
            },
        ]

        return cls.call_ai(
    messages=messages,
    json_mode=False,
)

    @classmethod
    def run_agent(cls, user, session, user_message):
        decision = cls.decide_tool(
            user=user,
            session=session,
            user_message=user_message,
        )

        tool_name = decision.get("tool", "none")
        arguments = decision.get("arguments", {})

        if tool_name == "none":
            tool_result = {
                "success": True,
                "message": decision.get(
                    "reason",
                    "No tool was needed for this message.",
                ),
            }
        else:
            tool_result = RecruitmentAgentTools.run_tool(
                tool_name=tool_name,
                user=user,
                arguments=arguments,
            )

        answer = cls.final_answer(
            user=user,
            user_message=user_message,
            tool_name=tool_name,
            tool_result=tool_result,
        )

        return {
            "answer": answer,
            "tool_name": tool_name,
            "tool_result": tool_result,
        }