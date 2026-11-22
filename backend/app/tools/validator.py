import re
import json
import hashlib
from typing import Dict, Any, Tuple, Optional
import jsonschema
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from app.core.logging import logger


class ToolSchemaValidator:
    """
    Validates tool execution arguments against the tool's JSON Schema specification.
    """
    @staticmethod
    def validate(parameters_schema: Dict[str, Any], arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not parameters_schema:
            return True, None
        try:
            jsonschema.validate(instance=arguments, schema=parameters_schema)
            return True, None
        except JsonSchemaValidationError as err:
            field = " -> ".join([str(p) for p in err.path]) if err.path else "root"
            msg = f"Schema validation failed at '{field}': {err.message}"
            return False, msg
        except Exception as exc:
            return False, f"Invalid schema or arguments: {str(exc)}"


class CanonicalArgumentHasher:
    """
    Generates a deterministic SHA-256 hash of tool arguments to bind approvals
    to the exact parameters. If arguments are modified even slightly, the hash changes.
    """
    @staticmethod
    def compute_hash(arguments: Dict[str, Any]) -> str:
        # Canonical JSON: keys sorted, no extra whitespace
        canonical_str = json.dumps(arguments, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

    @staticmethod
    def serialize_canonical(arguments: Dict[str, Any]) -> str:
        return json.dumps(arguments, sort_keys=True, separators=(',', ':'), default=str)


class SecretSanitizer:
    """
    Redacts credentials, tokens, and sensitive keys from logged payloads and UI records.
    """
    KEY_VALUE_PATTERN = re.compile(
        r'(?i)((?:api[_-]?key|token|secret|password|bearer|auth|authorization|private[_-]?key)["\']?\s*[:=]\s*["\']?)[^"\'\s,;]{4,}'
    )
    RAW_TOKEN_PATTERNS = [
        re.compile(r'sk-[a-zA-Z0-9_-]{20,}'),
        re.compile(r'ghp_[a-zA-Z0-9]{36}'),
        re.compile(r'xox[baprs]-[a-zA-Z0-9]{10,48}'),
    ]

    SENSITIVE_KEYS = {
        "password", "secret", "token", "api_key", "apikey", "access_token",
        "refresh_token", "private_key", "authorization", "auth", "secret_key"
    }

    @classmethod
    def sanitize_dict(cls, data: Any) -> Any:
        if isinstance(data, dict):
            sanitized = {}
            for k, v in data.items():
                if any(sk in k.lower() for sk in cls.SENSITIVE_KEYS):
                    sanitized[k] = "[REDACTED]"
                else:
                    sanitized[k] = cls.sanitize_dict(v)
            return sanitized
        elif isinstance(data, list):
            return [cls.sanitize_dict(item) for item in data]
        elif isinstance(data, str):
            return cls.sanitize_string(data)
        return data

    @classmethod
    def sanitize_string(cls, text: str) -> str:
        if not text:
            return text
        sanitized = cls.KEY_VALUE_PATTERN.sub(r'\1[REDACTED]', text)
        for pat in cls.RAW_TOKEN_PATTERNS:
            sanitized = pat.sub('[REDACTED]', sanitized)
        return sanitized

