import re
from typing import Dict, List, Set

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
from src.mglockne_story_line.util.entity_util import get_entity_categories


class HeuristicallyVerifyNamedEntitiesAreChangedCritique(BaseCritique):
    """
    Makes sure that all names that needed to be changed (at least in the verbatim form) do not exist anymore.
    """

    def __init__(self, name: str):
        super().__init__(name)

    def process(self, values: Dict) -> CritiqueResult:
        error_entities: List[Dict] = []
        renamed_entities: List[Dict] = [
            ent
            for entity_type in get_entity_categories()
            for ent in values[f'corrected_{entity_type}_name']
            if ent['name'] != ent['old_name']
        ]

        other_entity_names: Set[str] = {
            ent.name.lower()
            for entity_type in get_entity_categories()
            for ent in values[entity_type]
        } | {
            ent['name'].lower() for ent in renamed_entities
        }

        keep_renamed_entities_for_checking: List[Dict] = []
        for ent in renamed_entities:
            has_conflicts: bool = False
            old_name: str = ent['old_name'].lower()
            for name in other_entity_names:
                if old_name in name:
                    has_conflicts = True
                    break
            if not has_conflicts:
                keep_renamed_entities_for_checking.append(ent)

        text = ' '.join(values['story_item']).lower()
        for renamed_entity in keep_renamed_entities_for_checking:

            old_name: str = renamed_entity['old_name'].lower()
            pattern = re.compile(rf'\b{old_name}\b')
            still_has_old_name: bool = bool(re.search(pattern, text))
            if still_has_old_name:
                error_entities.append(renamed_entity)

        if len(error_entities) == 0:
            return CritiqueResult.correct(self.name)
        else:
            error_message: str = 'I found mentions of the following entities by their old names. Please refer to all entities only by their new names in the outline:\n'
            for ent in error_entities:
                error_message += f' - Old name: "{ent["old_name"]}"; New name: "{ent["name"]}".\n'
            return CritiqueResult(
                self.name, False, error_entities, error_message
            )
