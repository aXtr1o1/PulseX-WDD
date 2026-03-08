import json
import logging
from typing import List, Optional, Dict, Any, Generator
from openai import AzureOpenAI, OpenAI
from app.backend.config import Config
from app.backend.models import RouterOutput, Message

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = None
        self.embed_client = None
        self.deployment = None
        self.embed_deployment = None
        self.provider = "azure" # or 'openai'
        
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
            if self.provider == "azure":
                response = self.client.embeddings.create(
                    input=[text],
                    model=self.embed_deployment
                )
            else:
                response = self.client.embeddings.create(
                    input=[text],
                    model=self.embed_deployment
                )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return [0.0] * 1536

    def router_completion(self, user_message: str, history: List[Message] = None) -> RouterOutput:
        """
        Determines user intent and extracts entities strictly, using history for context.
        """
        history_str = ""
        if history is not None and len(history) > 0:
            history_str = "\n".join([f"{m.role}: {m.content}" for m in history])

        from datetime import datetime
        current_date = datetime.now().strftime("%B %d, %Y")
        system_prompt = f"""
        You are the Router for WDD PulseX.
        TODAY IS {current_date}.
        Classify user intent and extract filters based on the conversation history and current message.

        CONVERSATION HISTORY:
        {history_str}

        CURRENT MESSAGE:
        {user_message}
        
        Intents:
        - lead_capture: Detect buying/renting intent (triggers: "book visit", "call me", "send prices", "interested", "budget", "schedule", "I want", "booking").
        - project_query: asking facts about a specific project (location, amenities, units).
        - list_projects: Broad queries (e.g., "what properties do you have?", "list all projects", "show me villas").
        - compare: "compare project X and Y".
        - pricing: "how much is...", "what is the price of..." (if no explicit lead intent yet).
        - support_contact: "phone number", "complaint", "direct contact".
        
        Output Strict JSON:
        - intent: matches one of the above.
        - needs: list of fields user is asking for.
        - filters: {{project_type, project_status, region}}. 
          (Maintain filters from history if not overridden. e.g. if user previously said 'commercial', project_type should be 'commercial').
        - query_rewrite: clean, standalone search query that incorporates context from history if needed. 
          (e.g., if history shows 'commercial properties' and current message is 'West Cairo', rewrite to 'commercial properties in West Cairo').
          (If the message is broad like 'list all', keep the rewrite broad e.g. 'all properties').
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Contextualize: {user_message}"}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            # Ensure intent is present
            if "intent" not in data:
                data["intent"] = "project_query"
            return RouterOutput(**data)
        except Exception as e:
            logger.error(f"Router failed: {e}")
            return RouterOutput(
                intent="project_query",
                query_rewrite=user_message,
                needs=[],
                filters={},
                entities=[]
            )

    def answer_completion(
        self, 
        system_msg: str, 
        history: List[Message], 
        tools: Optional[List[Dict]] = None
    ) -> Any:
        """
        Generates answer using full history + optionally calls tools.
        Returns clean content string OR tool_calls object.
        """
        # Construct messages: System + History (excluding old systems if any)
        # We assume history comes from frontend as [User, Assistant, User...]
        # We prepend our fresh System Prompt.
        
        final_messages = [{"role": "system", "content": system_msg}]
        for m in history:
            # Ensure strict role/content structure
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
            
            # Check for tool usage
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
        """
        Streams answer tokens as they arrive from OpenAI.
        Yields text chunks for SSE streaming to the frontend.
        If a tool call is detected, yields the full tool call as JSON at the end.
        """
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
            
            tool_calls_buffer = {}  # Accumulate tool call chunks
            
            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue
                    
                # Text content
                if delta.content:
                    yield delta.content
                
                # Tool call chunks (accumulated)
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
            
            # If tool calls were accumulated, yield them as a special marker
            if tool_calls_buffer:
                yield f"\n__TOOL_CALLS__{json.dumps(list(tool_calls_buffer.values()))}"
                
        except Exception as e:
            logger.error(f"Stream answer completion failed: {e}")
            yield "I apologize, but I am having trouble connecting. Please try again."

llm_service = LLMService()
