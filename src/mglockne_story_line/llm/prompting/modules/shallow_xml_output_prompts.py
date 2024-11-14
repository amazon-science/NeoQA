
from typing import List, Dict, Union, Optional

from src.mglockne_story_line.llm.prompting.parsable_prompt import ParsablePrompt
from src.mglockne_story_line.llm.verifiers.unified_output_verifier import UnifiedOutputVerifier
from src.mglockne_story_line.util.xml_util import tag_sequence_to_dict


class ShallowXMLOutputPrompt(ParsablePrompt):
    """
    Base class for shallow outputs, i.e. XML without nesting.
    """

    def __init__(self, instructions: str, tag_list: List[str], name: str, return_type: str, verifier: Optional[UnifiedOutputVerifier] = None):
        super().__init__(instructions, return_type=return_type, name=name)
        self.tag_list: List[str] = tag_list
        self.verifier: Optional[UnifiedOutputVerifier] = verifier

    def parse(self, llm_output: str) -> Union[Dict, List[Dict]]:
        parsed: Union[Dict, List[Dict]] = self._parse(llm_output)

        if self.verifier is not None:
            if self.return_type == 'dict':
                verification_summary: Dict = self.verifier.check_structured_output(parsed)
                parsed['verification_summary'] = verification_summary

            elif self.return_type == 'list':
                for output in parsed:
                    output['verification_summary'] = self.verifier.check_structured_output(output)
            else:
                raise NotImplementedError(self.return_type)

        return parsed

    def _parse(self, llm_output: str) -> Union[Dict, List[Dict]]:
        raise NotImplementedError()


class ShallowXMLListOutputPrompt(ShallowXMLOutputPrompt):

    def __init__(self, instructions: str, tag_list: List[str], name: str, verifier: Optional[UnifiedOutputVerifier] = None):
        super().__init__(instructions, tag_list, name, 'list', verifier=verifier)

    def _parse(self, llm_output: str) -> List[Dict]:
        return tag_sequence_to_dict(llm_output, self.tag_list)


class ShallowXMLDictOutputPrompt(ShallowXMLOutputPrompt):
    def __init__(self, instructions: str, tag_list: List[str], name: str, verifier: Optional[UnifiedOutputVerifier] = None):
        super().__init__(instructions, tag_list, name, 'dict', verifier=verifier)

    def _parse(self, llm_output: str) -> Dict:
        output_dicts: List[Dict] = tag_sequence_to_dict(llm_output, self.tag_list)

        if len(output_dicts) > 1:
            raise ValueError(f'Expected not more than one answer entity but found {len(output_dicts)}!')
        return output_dicts[0]

