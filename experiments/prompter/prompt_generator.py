import re
from os.path import exists, join
from typing import Dict

from experiments.util.file_util import read_text_file


class PromptGenerator:
    def __init__(self, template_name: str, prompt_directory: str):
        if not template_name.endswith('.txt'):
            template_name += '.txt'

        template_path: str = join(prompt_directory, template_name)
        if not exists(template_path):
            raise ValueError(f'The template does not exist: "{template_path}"!')

        self.template: str = read_text_file(template_path).strip()

    def get_prompt(self, instance: Dict) -> Dict:

        prompt_values: Dict = self._prepare_prompt_values(instance)

        # Fill placeholders
        prompt: str = self.template[:]
        for key in prompt_values:
            repl = '{{' + key.upper() + '}}'
            if repl in prompt:
                prompt = prompt.replace(repl, prompt_values[key])

        # Make sure no placeholders are unfilled
        pattern_instruction_placeholder: re.Pattern = re.compile(r'\{\{\w+\}\}')
        placeholder_exist = bool(re.search(pattern_instruction_placeholder, prompt))
        if placeholder_exist:
            raise ValueError(f'Placeholder still exist in prompt: "{prompt}"')

        return {
            'prompt': prompt,
            'prompt_len': len(prompt)
        }

    def _prepare_prompt_values(self, instance: Dict) -> Dict:
        raise NotImplementedError

