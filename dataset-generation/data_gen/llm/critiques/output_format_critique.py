from typing import List, Optional, Dict, Union

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.llm.prompting.modules.nested_parsable_output_prompt import BasicNestedXMLParser, ParsePromptResultError


class OutputFormatCritique(BaseCritique):
    """
    Ensures that then output is properly formated:
    - Parsers must not throw any errors
    - If "min_number_results_total" is specified, at least this many results must have been found.
    """

    def __init__(
            self,
            name: str,
            parsers: List[BasicNestedXMLParser],
            expected_output_format_message: str,
            customized_format_messages: Optional[Dict[str, str]] = None,
            min_number_results_total: int = -1
    ):
        super().__init__(name)
        self.parsers: List[BasicNestedXMLParser] = parsers
        self.expected_output_format_message: str = expected_output_format_message
        self.customized_format_messages: Dict[str, str] = customized_format_messages or dict()
        self.min_number_results_total: int = min_number_results_total

    def process(self, values: Dict) -> CritiqueResult:
        response: str = values['response']
        error_messages: List[str] = []
        parser_errors: List[str] = []
        num_results: int = 0
        has_invalid_xml_error: bool = False

        for parser in self.parsers:
            try:
                result: Union[Dict, List] = parser.parse(response)
                if parser.to_single and result is not None:
                    num_results += 1
                else:
                    assert result is not None
                    num_results += len(result)

            except ParsePromptResultError:
                has_invalid_xml_error = True
                parser_errors.append(parser.name)
                if parser.name in self.customized_format_messages:
                    error_messages.append(self.customized_format_messages[parser.name])

        if len(parser_errors) == 0 and num_results >= self.min_number_results_total:
            return CritiqueResult.correct(self.name)
        elif num_results < self.min_number_results_total:
            err_message: str = self.expected_output_format_message
            if has_invalid_xml_error:
                err_message += '\nEnsure that special characters within the XML nodes (like "&") are properly escaped and encoded in UTF-8 to ensure the output can be parsed automatically. For example, instead of "Q&A" write "Q&amp;A".'
            return CritiqueResult(
                self.name, False, [{'num_results': num_results}], err_message
            )
        else:
            message = self.expected_output_format_message
            if has_invalid_xml_error:
                message += '\nEnsure that special characters within the XML nodes (like "&") are properly escaped and encoded in UTF-8 to ensure the output can be parsed automatically. For example, instead of "Q&A" write "Q&amp;A".'
            if len(error_messages) > 0:
                message += '\nFurther information:\n'
                for msg in error_messages:
                    message += f' - {msg}\n'
            return CritiqueResult(
                self.name,
                False,
                [{
                    p: self.customized_format_messages.get(p, None) for p in  parser_errors
                }],
                message
            )
