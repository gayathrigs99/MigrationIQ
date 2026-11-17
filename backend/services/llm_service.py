"""Gemini client returning validated, structured output."""

from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LlmResponseError(RuntimeError):
    """The model returned nothing usable for the requested schema."""


class GeminiLlmService:
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key or not model:
            raise ValueError("GEMINI_API_KEY and LLM_MODEL must be configured.")
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(self, prompt: str, schema: type[T]) -> T:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0,
            ),
        )
        if isinstance(response.parsed, schema):
            return response.parsed
        try:
            return schema.model_validate_json(response.text or "")
        except ValidationError as error:
            raise LlmResponseError(f"Model output did not match {schema.__name__}.") from error
