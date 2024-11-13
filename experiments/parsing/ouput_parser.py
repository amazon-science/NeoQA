from typing import Dict, List


class OutputParser:
    def select_answer(self, response: str, answer_choices: List[str]) -> Dict:
        raise NotImplementedError
