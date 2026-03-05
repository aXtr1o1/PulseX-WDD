"""
PulseX-WDD LLM Service — Azure OpenAI / OpenAI with output grammar enforcement.
Router completion removed (replaced by deterministic intent_router).
"""

import json
import logging
from typing import List, Optional, Dict, Any, Generator
from openai import AzureOpenAI, OpenAI
from app.backend.config import Config
from app.backend.models import Message

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.client = None
        self.embed_client = None
        self.deployment = None
        self.embed_deployment = None
        self.provider = "azure"
        self._setup_client()

    def _setup_client(self):
        # Try Azure first
        if Config.AZURE_OPENAI_API_KEY and Config.AZURE_OPENAI_ENDPOINT:
            try:
                self.client = AzureOpenAI(
                    api_key=Config.AZURE_OPENAI_API_KEY,
                    api_version=Config.AZURE_OPENAI_API_VERSION,
                    azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
                )
                self.deployment = Config.AZURE_OPENAI_CHAT_DEPLOYMENT
                self.embed_deployment = Config.AZURE_OPENAI_EMBED_DEPLOYMENT
                self.provider = "azure"
                logger.info("LLM Service initialized with Azure OpenAI")
                return
            except Exception as e:
                logger.warning(f"Failed to init Azure OpenAI: {e}")

        # Fallback to OpenAI
        if Config.OPENAI_API_KEY:
            self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
            self.deployment = Config.OPENAI_MODEL
            self.embed_deployment = Config.OPENAI_EMBED_MODEL
            self.provider = "openai"
            logger.info("LLM Service initialized with OpenAI Fallback")
        else:
            logger.error("No valid LLM credentials found.")

    def get_embedding(self, text: str) -> list[float]:
        text = text.replace("\n", " ")
        try:
            response = self.client.embeddings.create(
                input=[text],
                model=self.embed_deployment
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return [0.0] * 1536

    def answer_completion(
        self,
        system_msg: str,
        history: List[Message],
        tools: Optional[List[Dict]] = None
    ) -> Any:
        """Generate answer using full history. Returns content or tool_calls."""
        final_messages = [{"role": "system", "content": system_msg}]
        for m in history:
            final_messages.append({"role": m.role, "content": m.content})

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=final_messages,
                temperature=0.3,
                tools=tools,
                tool_choice="auto" if tools else None
            )

            message = response.choices[0].message
            if message.tool_calls:
                return message.tool_calls
            return message.content

        except Exception as e:
            logger.error(f"Answer completion failed: {e}")
            return "I apologize, but I am having trouble connecting. Please try again."

    def stream_answer_completion(
        self,
        system_msg: str,
        history: List[Message],
        tools: Optional[List[Dict]] = None
    ) -> Generator[str, None, None]:
        """Streams answer tokens via SSE. Accumulates tool calls."""
        final_messages = [{"role": "system", "content": system_msg}]
        for m in history:
            final_messages.append({"role": m.role, "content": m.content})

        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=final_messages,
                temperature=0.3,
                tools=tools,
                tool_choice="auto" if tools else None,
                stream=True
            )

            tool_calls_buffer = {}

            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                if delta.content:
                    yield delta.content

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {
                                "id": tc.id or "",
                                "function": {"name": "", "arguments": ""}
                            }
                        if tc.id:
                            tool_calls_buffer[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_buffer[idx]["function"]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_buffer[idx]["function"]["arguments"] += tc.function.arguments

            if tool_calls_buffer:
                yield f"\n__TOOL_CALLS__{json.dumps(list(tool_calls_buffer.values()))}"

        except Exception as e:
            logger.error(f"Stream answer completion failed: {e}")
            yield "I apologize, but I am having trouble connecting. Please try again."


llm_service = LLMService()
