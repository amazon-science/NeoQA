import re
from html import unescape
from typing import Union, Dict, List, Optional
import xml.etree.ElementTree as ET
from wave import Error

from data_gen.llm.prompting.parsable_prompt import ParsablePrompt
from data_gen.llm.verifier.named_unified_output_verifier import NamedUnifiedOutputVerifier
from data_gen.util.xml_util import extract_xml_content


def get_locator(locators: List[str], node: ET) -> str:
    locators = [
        (locator, len(node.findall(locator))) for locator in locators
    ]
    locators = sorted(locators, key=lambda x: -x[-1])
    return locators[0][0]


class ParsePromptResultError(Error):
    """
    Error class that is caught by the critiques.
    """
    pass


class BasicNestedXMLParser:
    """
    Parses the XML from an output.
    Can do preprocessing such as removing some content (<scratchpad>) or isolating a node (<result>).
    Depends on parsable XML.
    """
    def __init__(self,
                 name: str,
                 locator: str,
                 to_single: bool = False,
                 is_object: bool = True,
                 result_node: Optional[str] = None,
                 additional_locators_for_robustness: List[str] = None,
                 allow_empty_list: bool = True,
                 remove_node: Optional[str] = None,
                 require_fields: Optional[List[str]] = None,
                 shallow_text_extraction: bool = False
                 ):
        self.name: str = name
        self.locator: str = locator
        self.remove_node: str = remove_node
        self.additional_locators_for_robustness: List[str] = additional_locators_for_robustness or []
        self.to_single: bool = to_single
        self.is_object: bool = is_object
        self.result_node: Optional[str] = result_node
        self.allow_empty_list: bool = allow_empty_list
        self.require_fields: Optional[List[str]]  = require_fields
        self.shallow_text_extraction: bool = shallow_text_extraction
        if self.require_fields is not None and not self.is_object:
            print("WARING: require fields will be ignored (or set is_object=True)")

    def parse(self, s: str) -> Union[List, Dict, str]:

        if self.remove_node is not None:
            regexp_rm: re.Pattern = re.compile(r'<' + self.remove_node + r'>' + r'[\w\W]+?' + r'</' + self.remove_node + r'>')
            s = re.sub(regexp_rm, '', s)

        if self.shallow_text_extraction:
            pattern = re.compile(r'(<' + self.result_node + '>[\w\W]+</' + self.result_node + '>)')
            match = re.search(pattern, s)
            if match:
                s = match.group(1)
                return s.strip()
            else:
                raise ParsePromptResultError(f'Could not find "{self.result_node}"')

        if self.result_node is not None:
            extracted_s = extract_xml_content(s, self.result_node)
            if extracted_s is None:
                raise ParsePromptResultError(f'Could not find "{self.result_node}"')
            else:
                # Update s
                s = extracted_s

        s = s.strip()
        if s.startswith('Bot:'):
            s = s[4:].strip()
        try:
            root: ET = ET.fromstring(s)
        except Exception as err:
            raise ParsePromptResultError()
        parsed_list: List = []
        locator = get_locator([self.locator] + self.additional_locators_for_robustness, root)
        for node in root.findall(locator):
            if self.is_object:
                parsed_list.append({child.tag: unescape(child.text) if child.text else None for child in node})
                parsed_list = [elm for elm in parsed_list if len(elm) > 0]
            else:
                parsed_list.append(unescape(node.text.strip()))

        if self.is_object and self.require_fields is not None:
            for result in parsed_list:
                for field in self.require_fields:
                    if field not in result:
                        raise ParsePromptResultError(f'Make sure that at least these properties are included in {self.locator}: {self.require_fields}')

        if self.to_single:
            if len(parsed_list) == 1:
                return parsed_list[0]
            else:
                raise ParsePromptResultError(f'Want dictionary but got {len(parsed_list)} entries!')
        else:
            if len(parsed_list) == 0 and not self.allow_empty_list:
                raise ParsePromptResultError(f'Could not find any "{self.locator}"!')
            return parsed_list


class NestedParsablePrompt(ParsablePrompt):

    def __init__(
            self, instructions: str, name: str, parsers: List[BasicNestedXMLParser],
            named_output_verifiers: List[NamedUnifiedOutputVerifier]
    ):
        super().__init__(instructions, 'dict', name)
        self.parsers: List[BasicNestedXMLParser] = parsers
        self.named_output_verifiers: Dict[str, NamedUnifiedOutputVerifier] = {v.name: v for v in named_output_verifiers}

        if len(set(p.name for p in parsers)) != len(parsers):
            raise ValueError('Duplicate parser names!')

    def parse(self, llm_output: str) -> Union[Dict, List[Dict]]:
        out: Dict = dict()
        for parser in self.parsers:
            verifier: Optional[NamedUnifiedOutputVerifier] = self.named_output_verifiers.get(parser.name, None)
            parsed: Dict = parser.parse(llm_output)
            if verifier is not None:
                parsed['verification_summary'] = verifier.check_structured_output(parsed)
            out[parser.name] = parsed
        return out

