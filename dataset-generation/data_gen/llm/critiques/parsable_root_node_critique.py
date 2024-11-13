import re
from typing import Dict, Optional

import xml.etree.ElementTree as ET

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.util.xml_util import extract_xml_content


class ParsableRootNodeCritique(BaseCritique):
    """
    Checks that the root node is parsable and critiques otherwise.
    """

    def __init__(self, root_node: str, remove_node: Optional[str] = None, no_elaboration: bool = False):
        super().__init__('critique-parsable-xml')
        self.root_node: str = root_node
        self.remove_node: Optional[str] = remove_node
        self.no_elaboration: bool = no_elaboration

    def process(self, values: Dict) -> CritiqueResult:
        response: str = values['response']

        if self.remove_node is not None:
            regexp_rm: re.Pattern = re.compile(
                r'<' + self.remove_node + r'>' + r'[\w\W]+?' + r'</' + self.remove_node + r'>')
            response = re.sub(regexp_rm, '', response)

        s = extract_xml_content(response, self.root_node)
        if s is not None:
            try:
                ET.fromstring(s)
                return CritiqueResult.correct(self.name)
            except:
                error_message: str = f"Please ensure that all XML within the <{self.root_node}> root node is valid and can be automatically parsed. DO NOT refer to any XML nodes during your thinking process. DO NOT use the characters '<' or '>' during your thinking process! Now provide only the corrected output in the correct format without any extra explanation!"
                error_message += '\nEnsure that special characters within the XML nodes (like "&") are properly escaped and encoded in UTF-8 to ensure the output can be parsed automatically. For example, instead of "Q&A" write "Q&amp;A".'
                return CritiqueResult(self.name, False, [{'missing_root_node': self.root_node}], error_message)
        else:
            error_message: str = f'Please provide all your results within a single <{self.root_node}> root node.'
            if self.no_elaboration:
                error_message += f' Do not include any information other than the content within the <{self.root_node}> node.'
            return CritiqueResult(self.name, False, [{'missing_root_node': self.root_node}], error_message)

