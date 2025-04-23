from typing import Dict, List, Tuple


class BaseLLMWrapper:

    def __init__(self):
        self.count_queries: int = 0

    def query(self, system_prompt: str, prompt: str) -> Dict:
        raise NotImplementedError()

    def get_info(self) -> Dict:
        raise NotImplementedError()

    def query_history(self, system_prompt: str, prompt: str, history: List[Tuple[str, str]]) -> Dict:
        raise NotImplementedError()

    def reset_query_count(self):
        self.count_queries: int = 0