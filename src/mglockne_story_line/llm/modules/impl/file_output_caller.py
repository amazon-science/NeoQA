import os
from os import makedirs
from os.path import exists, join
from typing import Dict, Optional, List, Tuple

from src.mglockne_story_line.llm.modules.callable_module import CallableModule, FilePathModule
from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.util.file_util import read_json, store_json


class FileOutputCaller(CallableModule):
    """
    Calls an LLM and outputs the current status as a file.
    """
    def __init__(self, llm: BaseLLMWrapper, file_path_module: FilePathModule):
        self.llm: BaseLLMWrapper = llm
        self.file_path_module: FilePathModule = file_path_module

    def query(
            self,
            prompt: ParsablePrompt, values: Dict,
            output_directory: str,
            system_prompt: Optional[str] = None,
            params: Optional[Dict] = None,
            use_history: Optional[List[Tuple[str, str]]] = None,
            print_prompt: bool = False
    ) -> Dict:
        file_name: str = self.file_path_module.get_file_name(prompt, values)

        if not exists(output_directory):
            makedirs(output_directory)

        file_path: str = join(output_directory, file_name)
        if exists(file_path):
            os.remove(file_path)


        content = self._prompt_llm(prompt, values, system_prompt, file_path, use_history, print_prompt)



        content['cache_file_path'] = file_path
        return content

    def critique(self, critique_text: str, history: List[Tuple[str, str]], num_critique: int, cache_file_path: str):
        cached_content: Dict = read_json(cache_file_path)
        if 'critiques' not in cached_content:
            cached_content['critiques'] = []

        response: str = self.llm.query_history(None, critique_text.strip(), history)['response']
        cached_content['critiques'].append({'critique': critique_text.strip(), 'response': response})
        store_json(cached_content, cache_file_path, pretty=True)

        return response

    def _run_query(self, text_prompt, system_prompt: Optional[str], history: Optional[List[Tuple[str, str]]], file_path: str, print_prompt: bool):
        if history is None:
            out: Dict = self.llm.query(system_prompt, text_prompt)
        else:
            out: Dict = self.llm.query_history(system_prompt, text_prompt, history)
        if print_prompt:
            print('------------------------>> LLM RESPONSE <<-----------------')
            print(out['response'])
            print('------------------------>> END LLM RESPONSE <<-----------------')
        return out

    def _prompt_llm(self, prompt: ParsablePrompt, values: Dict, system_prompt: Optional[str], file_path: str, history: Optional[List[Tuple[str, str]]], print_prompt) -> Dict:
        text_prompt: str = prompt.get_prompt(values)

        if print_prompt:
            print('---------------- PROMPT --------------------')
            print(text_prompt)
            print('---------------- END PROMPT --------------------')

        out: Dict = self._run_query(text_prompt, system_prompt, history, file_path, print_prompt)
        response: str = out['response']
        content: Dict = {
            'llm': self.llm.get_info(),
            'llm-output': out,
            'response': response,
            'instructions': prompt.instructions,
            'text_prompt': text_prompt,
            'system-prompt': system_prompt,
            'values': values
        }

        store_json(content, file_path)
        return content


