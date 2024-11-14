import json
import re
from typing import List, Dict, Optional

from src.mglockne_story_line.inference.parse.mcq_extraction import MultipleChoiceAnswerSelector


def find_json_in_text(text):
    """
    Locates and extracts a JSON object from a text document.

    Args:
        text (str): The text containing the JSON object.

    Returns:
        dict: The parsed JSON object as a dictionary, or None if no valid JSON is found.
    """
    json_str = None
    try:
        # This regular expression matches the first JSON-like structure in the text
        json_pattern = r'{.*?}'
        match = re.search(json_pattern, text, re.DOTALL)

        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            return None
    except json.JSONDecodeError:
        if json_str is not None:
            answer_lines = [
                line for line in json_str.split('\n') if line.strip().startswith('"answer_choice"')
            ]
            if len(answer_lines) > 0:
                return json.loads('{' + answer_lines[0] + '}')
        else:
            pass
        return None


def clean_answer_choice(choice: str) -> str:
    choice = str(choice)
    for c in '[],.:()`\'"`':
        choice = choice.replace(c, '')
    return choice.strip()


class MultipleChoiceAnswerSelectorJSON:

    def __init__(self, num_answer_options: int):
        self.num_answer_options: int = num_answer_options
        self.backup: MultipleChoiceAnswerSelector = MultipleChoiceAnswerSelector(num_answer_options)

    def select_answer(self, response: str, answer_choices: List[str]) -> Dict:
        answer: Dict  = self.get_answer_from_json(response, answer_choices)
        if not answer['parsed']:
            answer = self.backup.select_answer(response, answer_choices)
        if not answer['parsed']:
            print("Could not parse:", response)
        return answer

    def get_answer_from_json(self, response: str, answer_choices: List[str]) -> Dict:
        response_json: Optional[Dict] = find_json_in_text(response)
        if response_json is None:
            pass
        if response_json is not None and 'answer_choice' in response_json:
            answer_choice = response_json['answer_choice']
            answer_choice = clean_answer_choice(answer_choice)
            for possible_answer in range(1, self.num_answer_options + 1):
                if answer_choice == str(possible_answer):
                    return {
                        'parsed': True, 'answered': possible_answer - 1
                    }

            # Default parser on the answer
            answer_choice = self.backup.select_answer(str(response_json['answer_choice']), answer_choices)
            return answer_choice
        return {
            'parsed': False, 'answered': -1
        }

