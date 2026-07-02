from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import BaseModel


class LLMConfig(BaseModel):
    provider: str
    pm_model: str
    critic_model: str


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int


class LLMClient(ABC):
    @abstractmethod
    def complete(
        self, system_prompt: str, messages: list[dict], model: str
    ) -> LLMResponse:
        raise NotImplementedError
