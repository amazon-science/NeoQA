import hashlib
import json
from typing import Dict, Optional, List

from experiments.llms.llm_cache import LLMHashCache


def hash_messages(messages: List[Dict], system_prompt: Optional[str] = None) -> str:
    message_tuples = []
    for message in messages:
        for key in sorted(list(message.keys())):
            message_tuples.append((key, message[key]))
    if system_prompt is not None:
        message_tuples = [('system', system_prompt)] + message_tuples
    hash_object = hashlib.sha256(repr(message_tuples).encode())
    return hash_object.hexdigest()


class LLM:

    def __init__(self, temperature: float, max_new_tokens: int):
        self.temperature: float = temperature
        self.max_new_tokens: int = max_new_tokens

    def generate(self, instance: Dict) -> str:
        raise NotImplementedError

    def get_name(self) -> str:
        raise NotImplementedError
