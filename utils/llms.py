"""
utils/llm.py — central LLM caller for the entire project (Groq version)
"""
from dotenv import load_dotenv

load_dotenv()
import os
import json
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from groq import Groq   

# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_MODEL ="llama-3.1-8b-instant"
DEFAULT_MAX_TOKENS = 1024

T = TypeVar("T", bound=BaseModel)

# ── Client (singleton) ────────────────────────────────────────────────────────

def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set.\n"
            "Run: export GROQ_API_KEY=your-key"
        )
    return Groq(api_key=api_key)

# ── Plain text call ───────────────────────────────────────────────────────────

def call_llm(
    prompt: str,
    system: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:

    client = _get_client()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


# ── Structured JSON call ──────────────────────────────────────────────────────

def call_llm_structured(
    prompt: str,
    schema: Type[T],
    system: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> T:

    field_lines = "\n".join(
        f'  "{name}": {field.annotation.__name__ if hasattr(field.annotation, "__name__") else str(field.annotation)}'
        for name, field in schema.model_fields.items()
    )

    schema_block = f"""Return ONLY a valid JSON object with this exact structure:
{{
{field_lines}
}}"""

    full_prompt = f"{prompt}\n\n{schema_block}\n\nNo explanation. No markdown. Just the JSON object."

    client = _get_client()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": full_prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON.\nRaw response:\n{raw}\nError: {e}"
        )

    try:
        return schema(**data)
    except Exception as e:
        raise ValueError(
            f"JSON does not match schema {schema.__name__}.\nData: {data}\nError: {e}"
        )


# ── Multi-item structured call ────────────────────────────────────────────────

def call_llm_structured_list(
    prompt: str,
    schema: Type[T],
    system: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[T]:

    field_lines = "\n".join(
        f'  "{name}": {field.annotation.__name__ if hasattr(field.annotation, "__name__") else str(field.annotation)}'
        for name, field in schema.model_fields.items()
    )

    schema_block = f"""Return ONLY a valid JSON array where each item has this structure:
{{
{field_lines}
}}
Example format: [{{...}}, {{...}}]"""

    full_prompt = f"{prompt}\n\n{schema_block}\n\nNo explanation. No markdown. Just the JSON array."

    client = _get_client()

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": full_prompt})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON.\nRaw:\n{raw}\nError: {e}")

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got: {type(data)}")

    return [schema(**item) for item in data]