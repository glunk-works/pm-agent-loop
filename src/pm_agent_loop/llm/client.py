from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMConfig(BaseModel):
    provider: str
    pm_model: str
    critic_model: str


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system_prompt: str, messages: list[dict], model: str) -> str:
        raise NotImplementedError
