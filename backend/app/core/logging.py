import logging
import re
import json
from typing import Any, Dict

# Regex pattern to identify sensitive keys and API tokens
SENSITIVE_KEY_PATTERN = re.compile(
    r'(api_key|key|secret|password|auth|authorization|token|bearer|openai_api_key)',
    re.IGNORECASE
)

SENSITIVE_VALUE_PATTERN = re.compile(
    r'(sk-[a-zA-Z0-9T3BlbkFJ]{20,}|Bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*)',
    re.IGNORECASE
)


class MaskingFormatter(logging.Formatter):
    """Logging formatter that automatically masks API keys and sensitive tokens."""

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        return self.mask_sensitive_data(msg)

    @classmethod
    def mask_sensitive_data(cls, text: str) -> str:
        if not text:
            return text

        # Mask explicit secret values (e.g., OpenAI API key format sk-...)
        text = SENSITIVE_VALUE_PATTERN.sub('[REDACTED_API_KEY]', text)

        # Mask JSON keys containing sensitive terms
        try:
            if text.startswith('{') and text.endswith('}'):
                data = json.loads(text)
                masked_data = cls._mask_dict(data)
                return json.dumps(masked_data)
        except Exception:
            pass

        return text

    @classmethod
    def _mask_dict(cls, d: Dict[str, Any]) -> Dict[str, Any]:
        masked = {}
        for k, v in d.items():
            if SENSITIVE_KEY_PATTERN.search(str(k)):
                masked[k] = "[REDACTED]"
            elif isinstance(v, dict):
                masked[k] = cls._mask_dict(v)
            elif isinstance(v, list):
                masked[k] = [cls._mask_dict(item) if isinstance(item, dict) else item for item in v]
            else:
                masked[k] = v
        return masked


def get_logger(name: str = "factlens") -> logging.Logger:
    """Get a configured logger instance with automated data masking."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = MaskingFormatter(
            fmt='[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
