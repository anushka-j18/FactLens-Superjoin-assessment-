import json
import time
from typing import Dict, Any, Optional
from app.services.llm.base import LLMProvider
from app.core.logging import get_logger
from app.config import settings

logger = get_logger(__name__)


class OpenAILLMProvider(LLMProvider):
    """OpenAI LLM provider implementation with automatic retry behavior for transient failures."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", max_retries: int = 3):
        self.api_key = api_key or getattr(settings, "OPENAI_API_KEY", "")
        self.model = model
        self.max_retries = max_retries

    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text completion with exponential backoff retries via HTTP API."""
        if not self.api_key or self.api_key.startswith("your_openai_api_key"):
            raise ValueError("OpenAI API key is missing or not configured in .env.")

        attempts = 0
        last_exception = None

        while attempts < self.max_retries:
            try:
                attempts += 1
                import httpx
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                }

                with httpx.Client(timeout=60.0) as client:
                    resp = client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
                    if resp.status_code != 200:
                        raise RuntimeError(f"OpenAI API returned status {resp.status_code}: {resp.text}")
                    data = resp.json()
                    return data["choices"][0]["message"]["content"] or ""
            except Exception as e:
                last_exception = e
                logger.warning(f"OpenAI completion attempt {attempts}/{self.max_retries} failed: {str(e)}")
                if attempts < self.max_retries:
                    time.sleep(1.0 * (2 ** (attempts - 1)))

        logger.error(f"OpenAI completion exhausted retries: {str(last_exception)}")
        raise RuntimeError(f"OpenAI LLM provider failed after {self.max_retries} retries: {str(last_exception)}")

    def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON adhering to schema with retry behavior."""
        attempts = 0
        last_exception = None

        sys_msg = (system_prompt or "") + f"\nOutput ONLY valid JSON adhering strictly to schema: {json.dumps(schema)}"

        while attempts < self.max_retries:
            try:
                attempts += 1
                raw_text = self.generate_completion(prompt, system_prompt=sys_msg)
                
                # Strip markdown code blocks if present
                clean_json = raw_text.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()

                return json.loads(clean_json)
            except json.JSONDecodeError as je:
                last_exception = je
                logger.warning(f"Structured output JSON parse attempt {attempts}/{self.max_retries} failed: {str(je)}")
                if attempts < self.max_retries:
                    time.sleep(1.0 * (2 ** (attempts - 1)))
            except Exception as e:
                last_exception = e
                logger.warning(f"Structured output attempt {attempts}/{self.max_retries} failed: {str(e)}")
                if attempts < self.max_retries:
                    time.sleep(1.0 * (2 ** (attempts - 1)))

        logger.error(f"OpenAI structured generation exhausted retries: {str(last_exception)}")
        raise RuntimeError(f"OpenAI LLM structured generation failed after {self.max_retries} retries: {str(last_exception)}")
