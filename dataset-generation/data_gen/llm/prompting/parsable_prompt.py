import re
from typing import Optional, Dict, Union, List


class ParsablePrompt:
    """
    Instructions that come with their parsers.
    """
    def __init__(self, instructions: str, return_type: str, name: str):
        self.instructions: str = instructions
        self.return_type: str = return_type
        self.name: str = name
        self.pattern_instruction_placeholder: re.Pattern = re.compile(r'\{\{\w+\}\}')

    def get_prompt(self, values: Optional[Dict] = None, allow_placeholder: bool = False):
        if values is None:
            prompt: str = self.instructions
        else:
            prompt : str = self.instructions[:]
            for key in values.keys():
                repl_key: str = '{{' + str(key) + '}}'
                prompt = prompt.replace(repl_key, str(values[key]))

        placeholder_exist = bool(re.search(self.pattern_instruction_placeholder, prompt))
        if placeholder_exist and not allow_placeholder:
            raise ValueError(f'Placeholder still exist in prompt: "{prompt}"')

        return prompt

    def parse(self, llm_output: str) -> Union[Dict, List[Dict]]:
        raise NotImplementedError()
