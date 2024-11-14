import re
from typing import Dict, Callable, List


class AnswerChoiceSelector:
    def __init__(self, choices):
        self.choices = choices

    def get_token_positions(self, text):
        positions = []
        for i, answer in enumerate(self.choices):
            for match in re.finditer(rf'\b{re.escape(answer)}\b', text):
                positions.append((i, match.group().strip(), match.start()))
        return sorted(positions, key=lambda x: x[-1])


    def get_single_answer_token(self, text):
        found = list(set([
            idx for idx, _, _ in self.get_token_positions(text)
        ]))
        if len(found) == 1:
            return found[0]
        return -1


class MultipleChoiceAnswerSelector:

    def __init__(self, num_answer_options: int):
        self.num_answer_options: int = num_answer_options

    def select_answer(self, response: str, answer_choices: List[str]) -> Dict:
        selector: AnswerChoiceSelector = AnswerChoiceSelector(answer_choices)
        parse_fns: List[Callable[[str], int]] = [
            self.get_num_if_exists,
            self.first_line_is_answer,
            self.any_single_line_is_answer,
            self.starts_with_num,
            self.single_bracket_num,
            selector.get_single_answer_token,
            self.first_bracket_num,
            self.first_single_line
        ]

        answer_idx: int = -1
        for _parse in parse_fns:
            answer_idx = _parse(response)
            if answer_idx > -1:
                return {
                    'parsed': True,
                    'answered': answer_idx
                }


        has_num = False
        for i in range(1, self.num_answer_options + 1):
            has_num = has_num or str(i) in response

        if has_num and answer_idx < 0:
            print("RESPONSE WITH NUM::")
            print(response.strip())
        elif answer_idx < 0:
            print('Response>')
            print(response.strip())
            print('END\n')
        return {
            'parsed': False,
            'answered': -1
        }

    def parse_response(self, original_response: str) -> int:
        response: str = original_response
        for c in '[],.:()`\'"`':
            response = response.replace(c, '')
        response = response.strip().split('\n')[0]
        response = response.strip()

        for answer in range(1, self.num_answer_options + 1):
            if response == str(answer):
                return answer - 1
        return -1

    def get_num_if_exists(self, text: str) -> int:
        for c in '[],.:()`\'"`':
            text = text.replace(c, '')
        text = text.strip()
        for answer in range(1, self.num_answer_options + 1):
            if text == str(answer):
                return answer - 1
        return -1

    def first_line_is_answer(self, text: str):
        return self.get_num_if_exists(text.strip().split('\n')[0])

    def first_single_line(self, text):
        for line in text.strip('\n'):
            answer = self.get_num_if_exists(line)
            if answer > -1:
                return answer
        return -1

    def starts_with_num(self, text: str) -> int:
        return self.get_num_if_exists(text.strip().split(' ')[0])

    def answer_number(self, text: str):
        nums = [
            num - 1 for num in range(1, self.num_answer_options + 1) if f'number: {num}' in text.lower()
        ]
        if len(nums) == 1:
            return nums[0]
        return -1

    def single_bracket_num(self, text: str):
        nums = [
            num - 1 for num in range(1, self.num_answer_options + 1)
            if f'[{num}]' in text
        ]
        if len(nums) == 1:
            return nums[0]
        return -1

    def first_bracket_num(self, text):
        nums = [
            (num - 1, text.index(f'[{num}]')) for num in range(1, self.num_answer_options + 1)if f'[{num}]' in text
        ]
        nums = [
            n for n in nums if n[-1] >= 0
        ]
        nums = sorted(nums, key=lambda x: x[-1])
        if len(nums) > 0:
            answer = nums[0][0]
            return answer
        return -1

    def any_single_line_is_answer(self, text: str):
        lines = [
            line for line in text.split('\n') if len(line.strip()) > 0
        ]
        for line in lines:
            answer: int  =  self.get_num_if_exists(line)
            if answer > -1:
                return answer
        return -1

