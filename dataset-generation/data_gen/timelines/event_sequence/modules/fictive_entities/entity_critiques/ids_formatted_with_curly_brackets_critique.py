import re
from typing import *

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.util.entity_util import get_entity_categories


class EntityIdsAreFormattedWithCurlyBracketsCritique(BaseCritique):
    """
    MAke sure that only expected IDs of named entities exist in the outline.
    """

    def process(self, values: Dict) -> CritiqueResult:

        problematic_ids: Set[str] = set()
        for story_item in values['story_item']:
            print('STORY-ITEM:', story_item)
            for pattern in self.reg_exprs:
                matches = list(re.finditer(pattern, story_item))
                for match in matches:
                    problematic_ids.add(match.group(1))

        problematic_ids_list: List[str] = sorted(list(problematic_ids))

        if len(problematic_ids_list) == 0:
            return CritiqueResult.correct(self.name)
        else:
            message: str = 'The following named entities do not appear to be in the correct format. Please encode all references to these named entities along with their ID in the following format: {full name|ID}. Remember to include the curly brackets ({ and }). The curly bracket may be omitted for the following IDs:\n'
            for _id in problematic_ids_list:
                message += f' - "{_id}"\n'
            return CritiqueResult(
                self.name, False, [{'id': _id} for _id in problematic_ids_list], message
            )

    def __init__(self):
        super().__init__('idfy-outline-too-many-ids')
        self.reg_exprs: List[re.Pattern] = [
            rf'\|({entity_type.upper()}' + r'-\d{1,2})(?!\d|\})'
            for entity_type in get_entity_categories()
        ]
