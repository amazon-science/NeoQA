import re
from typing import List, Dict, Callable


from experiments.parsing.ouput_parser import OutputParser


class LastLineOutputParser(OutputParser):

    def __init__(self, num_answer_options: int):
        self.num_answer_options: int = num_answer_options

    def select_answer(self, response: str, answer_choices: List[str]) -> Dict:

        parsed: int = -1

        if parsed < 0:
            parsed = self.extract_single_digit_number(response)

        if parsed < 0:
            parsed = self.select_multi_line(response)

        if parsed < 0:
            parsed = self.select_by_option_text(response, answer_choices)

        if parsed == -1:
            print(answer_choices)

        return {
            'parsed': parsed >= 0,
            'answered': parsed
        }


    def extract_single_digit_number(self, text):
        """
        Extracts a single-digit number from a string starting with 'Answer:'.
        The square brackets around the number are optional.

        Args:
            text (str): The input string.

        Returns:
            int: The single-digit number if found, or None otherwise.
        """

        lines = text.strip().split('\n')[::-1]
        for line in lines:
            line = line.replace('*', '').strip().lower()
            match = re.match(r'^(?:answer:\s*)+\[?(\d)\]?', line)
            if match:
                answered: int = int(match.group(1)) - 1
                if answered < self.num_answer_options:
                    return answered
        return -1

    def select_multi_line(self, text: str):
        text = text.lower().strip()
        match = re.search(r'\*?\*?answer:\*?\*?\s*\[?(\d)\]?', text)
        if match:
            answer: int = int(match.group(1)) - 1
            if answer < self.num_answer_options:
                return answer
        return -1

    def select_by_option_text(self, text: str, options: List[str]):
        options = sorted(options, key=lambda x: -len(x))

        text = text.lower()
        for i, opt in enumerate(options):
            if re.search(rf'\s*answer\*?\*?:\*?\*?\s*{re.escape(opt.lower())}', text):
                return i
        return -1


