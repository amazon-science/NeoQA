from copy import deepcopy
from datetime import datetime
from os.path import join
from typing import List, Dict, Optional, Tuple

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.llm.critiques.unified_critique_module import XMlParseError, UnifiedCritiqueModule
from data_gen.llm.modules.callable_module import FilePathModule, CallableModule
from data_gen.llm.modules.impl.file_output_caller import FileOutputCaller
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import ParsePromptResultError, NestedParsablePrompt, \
    BasicNestedXMLParser
from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.verifier.named_unified_output_verifier import NamedUnifiedOutputVerifier
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.util.file_util import slugify


class ParsableBaseModule(CallableModule, FilePathModule):
    """
    Base class for all modules that query the LLM.
    """

    def reset(self, history_enabled: bool = False):
        self.skip = False
        self.print_prompt = True
        self.history_enabled = history_enabled
        self.history = []
        self.unified_critique = UnifiedCritiqueModule(
            self.critiques, self.format_critique, self.max_critiques, self.critique_text
        )

    def __init__(
            self,
            llm: BaseLLMWrapper,
            name: str,
            instruction_name: str,
            instructions: str,
            max_critiques: int = 5,
            is_correction_module: bool = False,
            critique_text: str = 'v1',
            allow_parse_error: bool = False
    ):
        super().__init__()
        self.critique_text: str = critique_text
        self.instruction_name: str = instruction_name
        self.instructions: str = instructions
        self.max_critiques: int = max_critiques
        self.name: str = name
        self.critiques: List[BaseCritique] = self._create_critiques()
        self.format_critique = self._create_formatting_critique(self._get_parsers())
        self.caller: FileOutputCaller = FileOutputCaller(llm, self)

        self.unified_critique: UnifiedCritiqueModule = UnifiedCritiqueModule(
            self.critiques, self.format_critique, self.max_critiques, self.critique_text
        )
        self.history: List[Tuple[str, str]] = []
        self.is_correction_module: bool = is_correction_module
        if is_correction_module and len(self.critiques) == 0:
            raise ValueError(f'Correction Modules must provide critiques!')
        self.skip: bool = False
        self.history_enabled: bool = False
        self.print_prompt: bool = True
        self.allow_parse_error: bool = allow_parse_error

    def set_history(self, history: List[Tuple[str, str]]):
        self.history = history

    def set_history_enabled(self, enabled: bool):
        self.history_enabled = enabled

    def _preprocess_values(self, values) -> Dict:
        return values

    def _postprocess_values(self, values: Dict) -> Optional[Dict]:
        return values

    def on_called(self, values: Dict) -> Dict:
        return values

    def on_critique_called(self, values: Dict):
        return values

    def on_main_called(self, values: Dict):
        return values

    def query(
            self,
            prompt: ParsablePrompt, values: Dict,
            output_directory: str,
            system_prompt: Optional[str] = None,
            params: Optional[Dict] = None,
            use_history: Optional[List[Tuple[str, str]]] = None,
            print_prompt: bool = False
    ) -> Dict:
        out: Dict = self.caller.query(
            prompt,
            values,
            output_directory,
            system_prompt,
            params,
            use_history,
            print_prompt
        )
        self.history.append((out['text_prompt'], out['response']))
        valid_format_critique_result: CritiqueResult = self.unified_critique.has_valid_format(out['response'])
        if not valid_format_critique_result.is_valid:
            output_file: str = join(
                output_directory,
                slugify(self.caller.file_path_module.get_file_name(prompt, values))
            )
            out['response'] = self.unified_critique.get_valid_format(
                self, output_file, valid_format_critique_result
            )

        try:
            out = self._parse_llm_output(out, prompt)
        except ParsePromptResultError as err:
            out['error'] = err
            out['parsed'] = None
            return out

        self.spy_on_output(out)
        out['info'] = params or dict()
        return out

    def spy_on_output(self, output: Dict):
        pass

    def _parse_llm_output(self, content: Dict, prompt: ParsablePrompt):
        content['parsed'] = prompt.parse(content['response'])
        return content

    def critique(self, critique_text: str, history: List[Tuple[str, str]], num_critique: int, cache_file_path: str) -> str:
        critique_text = critique_text.strip()
        return self.caller.critique(critique_text, history, num_critique, cache_file_path)

    def call(self, values: Dict, output_directory: str) -> Dict:
        try:
            if not self.history_enabled:
                self.history = []

            self.unified_critique.set_history(self.history)
            values = self._preprocess_values(deepcopy(values))
            if self.skip:
                return values

            if self.is_correction_module:
                is_valid: bool = self.unified_critique.verify(values)

                # No need to run correction module
                if is_valid:
                    return values
                else:
                    issues: List[Dict] = self.unified_critique.last_validity_issues()
                    values = self._on_start_validated_found_errors(values, issues)

            prompt: NestedParsablePrompt = NestedParsablePrompt(
                self.instructions,
                self.instruction_name,
                self._get_parsers(),
                self._get_verifiers()
            )

            start_num_critiqued = self.unified_critique.num_critiqued
            new_content = self.query(
                prompt,
                {key.upper(): values[key] for key in values.keys()},
                output_directory,
                use_history=self.history,
                print_prompt=self.print_prompt,
                system_prompt=self._get_system_prompt(values)
            )

            start_post_call = datetime.now()
            if new_content['parsed'] is None:
                raise ValueError('Could not be parsed')
            values = {**values, **new_content['parsed']}
            values = self.on_main_called(values)
            values = self.unified_critique.update_values(values)
            values = self.on_called(values)
            is_valid: bool = self.unified_critique.verify(values, new_content['response'])

            self.unified_critique.set_history(self.history)

            # For Windows (26.11)
            new_content['cache_file_path'] = new_content['cache_file_path'].replace('"', '').replace("'", '')
            cache_file_path: str = new_content['cache_file_path']
            end_post_call = datetime.now()
            while not is_valid and self.unified_critique.can_critique_more():
                values = self.on_call_critiques(values, self.unified_critique.get_critique_text())
                new_content = self.unified_critique.critique_content(prompt, self, cache_file_path)
                values = {**values, **new_content}
                values = self.on_critique_called(values)
                values = self.unified_critique.update_values(values)
                values = self.on_called(values)
                is_valid = self.unified_critique.verify(values, new_content['response'])

            self.history = self.unified_critique.get_history()
            end_validate = datetime.now()
            if is_valid:
                values['is_valid'] = True
                values = self._postprocess_values(values)
            else:
                values['is_valid'] = False
                values['validity_issues'] = self.unified_critique.last_validity_issues()
                raise NotImplementedError(
                    'This error indicates that some output was not as expected but no recover strategy was implemented.'
                )
        except XMlParseError as err:
            if self.allow_parse_error:
                return {
                    'is_valid': False
                }
            else:
                raise err

        return values

    def on_call_critiques(self, values: Dict, critique_text: str) -> Dict:
        return values

    def _on_start_validated_found_errors(self, values: Dict, issues: List[Dict]):
        return values

    def _get_system_prompt(self, values: Dict) -> Optional[str]:
        return None

    def _create_critiques(self) -> List[BaseCritique]:
        return []

    def _create_formatting_critique(self, parsers: List[BasicNestedXMLParser]) -> Optional[BaseCritique]:
        return None

    def _get_parsers(self) -> List[BasicNestedXMLParser]:
        raise NotImplementedError()

    def _get_verifiers(self) -> List[NamedUnifiedOutputVerifier]:
        return []

    def get_file_name(self, prompt: ParsablePrompt, values: Dict):
        raise NotImplementedError()
