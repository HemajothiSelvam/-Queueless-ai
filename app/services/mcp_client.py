"""
MCP Client — Model Context Protocol implementation.

MCP defines a standard way for AI agents to call tools and receive
structured responses. Here we implement an MCP client that:
1. Defines available tools (queue_insights, slot_recommendation)
2. Sends tool call requests to OpenAI GPT-4o
3. Parses and returns structured responses

This follows the MCP spec: https://modelcontextprotocol.io
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

# MCP Tool definitions — these describe what the AI can do
MCP_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "queue_insights",
            "description": "Generate natural-language insights about hospital queue patterns for a specific department",
            "parameters": {
                "type": "object",
                "properties": {
                    "hospital_name": {"type": "string", "description": "Name of the hospital"},
                    "department": {"type": "string", "description": "Department/service name"},
                    "avg_wait_minutes": {"type": "number", "description": "Average wait time in minutes"},
                    "peak_hour": {"type": "string", "description": "Busiest hour e.g. '10:00'"},
                    "best_slot": {"type": "string", "description": "Recommended slot e.g. '09:00'"},
                    "total_patients_30d": {"type": "integer", "description": "Total patients in past 30 days"}
                },
                "required": ["hospital_name", "department", "avg_wait_minutes"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slot_recommendation",
            "description": "Recommend the best appointment slot for a patient based on queue data",
            "parameters": {
                "type": "object",
                "properties": {
                    "available_slots": {"type": "array", "items": {"type": "string"}, "description": "List of available time slots"},
                    "crowd_scores": {"type": "array", "items": {"type": "number"}, "description": "Crowd score for each slot (lower = less crowded)"},
                    "patient_preference": {"type": "string", "description": "Patient's preferred time of day: morning/afternoon/any"}
                },
                "required": ["available_slots", "crowd_scores"]
            }
        }
    }
]


class MCPClient:
    """
    MCP Client that communicates with OpenAI GPT-4o using the
    Model Context Protocol tool-calling pattern.

    In MCP architecture:
    - This class = MCP Client
    - OpenAI API = MCP Server
    - MCP_TOOLS = Tool definitions exposed by the server
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._client = None

    def _get_client(self):
        """Lazy-load OpenAI client."""
        if not self._client:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                logger.warning("openai package not installed. Using fallback mode.")
                return None
        return self._client

    def call_tool(self, tool_name: str, tool_args: dict) -> dict:
        """
        Execute an MCP tool call.

        Sends a structured request to the LLM asking it to use
        a specific tool with given arguments, then returns the result.
        """
        client = self._get_client()

        if not client or not self.api_key:
            logger.info("MCP: No API key — using fallback response")
            return self._fallback_response(tool_name, tool_args)

        try:
            # MCP Step 1: Send tool call request to the server (LLM)
            logger.info(f"MCP: Calling tool '{tool_name}' with args: {tool_args}")

            messages = [
                {
                    "role": "system",
                    "content": "You are a hospital queue management AI assistant. Use the provided tools to generate helpful insights for patients and staff."
                },
                {
                    "role": "user",
                    "content": f"Please use the {tool_name} tool with the provided data to generate a response."
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_001",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_args)
                            }
                        }
                    ]
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_001",
                    "content": json.dumps(tool_args)
                }
            ]

            # MCP Step 2: Get structured response from server
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=MCP_TOOLS,
                max_tokens=300
            )

            result_text = response.choices[0].message.content or ""
            logger.info(f"MCP: Tool '{tool_name}' returned response")

            return {"success": True, "result": result_text, "tool": tool_name}

        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            return self._fallback_response(tool_name, tool_args)

    def _fallback_response(self, tool_name: str, tool_args: dict) -> dict:
        """Template-based fallback when OpenAI is unavailable."""
        if tool_name == "queue_insights":
            hospital = tool_args.get("hospital_name", "this hospital")
            dept = tool_args.get("department", "this department")
            avg_wait = tool_args.get("avg_wait_minutes", 0)
            peak = tool_args.get("peak_hour", "11:00")
            best = tool_args.get("best_slot", "09:00")
            total = tool_args.get("total_patients_30d", 0)
            result = (
                f"At {hospital}, {dept} sees approximately {round(total/30, 1)} patients per day "
                f"with an average wait of {avg_wait} minutes. "
                f"The busiest time is around {peak}. "
                f"For the shortest wait, we recommend booking at {best}."
            )
        elif tool_name == "slot_recommendation":
            slots = tool_args.get("available_slots", [])
            scores = tool_args.get("crowd_scores", [])
            if slots and scores:
                best_idx = scores.index(min(scores))
                best = slots[best_idx]
                result = f"Based on current queue patterns, {best} is the best slot with the lowest expected crowd."
            else:
                result = "Please select a time slot that works best for you."
        else:
            result = "AI insights are currently unavailable."

        return {"success": True, "result": result, "tool": tool_name, "fallback": True}


# Singleton instance
mcp_client = MCPClient()
