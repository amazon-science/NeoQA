from typing import Dict

from experiments.llms.llm import LLM


class DummyLLM(LLM):

    def __init__(self):
        super().__init__(temperature=0.0, max_new_tokens=0)

    def generate(self, instance: Dict) -> str:
        return f'Answer: 3'

    def get_name(self) -> str:
        return "static-1"