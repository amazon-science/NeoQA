import re
from typing import Dict, List, Set

from markdown_it.rules_inline import entity

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
from src.mglockne_story_line.util.entity_util import get_entity_categories


class IdfyOutlineTooManyIdsCritique(BaseCritique):
    """
    MAke sure that only expected IDs of named entities exist in the outline.
    """

    def process(self, values: Dict) -> CritiqueResult:
        known_ids: Set[str] = {
            ent['id']
            for entity_type in get_entity_categories()
            for ent in values[f'used-name-and-id-for-{entity_type}']
        }

        found_ids = set()
        text: str = ' '.join(values['story_item'])
        for pattern in self.reg_exprs:
            for match in re.finditer(pattern, text):
                found_ids.add(match.group(1))

            # Check if they have a masked counterpart!
        hallucinated_ids: List[str] = sorted(list(found_ids - known_ids))

        if len(hallucinated_ids) == 0:
            return CritiqueResult.correct(self.name)
        else:
            message: str = f'Only mark the entities listed in <entities>. The following entities were marked but are not in the provided list:\n'
            for _id in hallucinated_ids:
                message += f' - "{_id}"\n'
            return CritiqueResult(
                self.name, False, [{'id': _id} for _id in hallucinated_ids], message
            )

    def __init__(self):
        super().__init__('idfy-outline-too-many-ids')
        self.reg_exprs: List[re.Pattern] = [
            re.compile(rf'\|({entity_type.upper()}-\d+)' + r'\}')
            for entity_type in get_entity_categories()
        ]
