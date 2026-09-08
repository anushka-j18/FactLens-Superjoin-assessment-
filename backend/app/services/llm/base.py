from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    Allows switching between OpenAI, Anthropic, Gemini, or Mock providers
    without modifying downstream fact extraction or reasoning logic.
    """
    
    @abstractmethod
    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a raw text completion."""
        pass
        
    @abstractmethod
    def generate_structured(
        self, 
        prompt: str, 
        schema: Dict[str, Any], 
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON output adhering to a schema."""
        pass
