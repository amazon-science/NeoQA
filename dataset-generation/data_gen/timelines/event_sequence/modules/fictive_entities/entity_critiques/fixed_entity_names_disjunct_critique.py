from collections import defaultdict
from typing import Dict, List

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.util.entity_util import get_entity_categories


class CheckThatDifferentNamedEntitiesHaveDifferentNamesCritique(BaseCritique):
    """
    Make sure that the LLM did not change the name of different named entities to the same new name.
    """
    def process(self, values: Dict) -> CritiqueResult:

        name_to_old_name: Dict[str, List[str]] = defaultdict(list)
        for entity_type in get_entity_categories():
            new_entity_names: List[Dict] = values[f'corrected_{entity_type}_name']
            for ent_name in new_entity_names:
                name_to_old_name[ent_name['name'].strip()].append(ent_name['old_name'])

        duplicate_names: List[str] = [
            name for name in name_to_old_name.keys() if len(name_to_old_name[name]) > 1
        ]

        if len(duplicate_names) == 0:
            return CritiqueResult.correct(self.name)
        else:
            error_message: str = "You have assigned the same name to different entities. Please ensure each entity has a unique name.\n"
            error_message += 'Here are the entities with identical names:\n'
            for name in duplicate_names:
                old_names: str = ', '.join([
                    f'"{t}"' for t in name_to_old_name[name]
                ])
                error_message += f'The new name "{name}" has the previous names: {old_names}.'

            return CritiqueResult(self.name, False, [{name: name_to_old_name[name]} for name in duplicate_names],
                                  error_message)

    def __init__(self):
        super().__init__('find-same-entity-as-different-types-critique')