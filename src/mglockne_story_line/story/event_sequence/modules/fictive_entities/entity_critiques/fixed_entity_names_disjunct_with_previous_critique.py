from typing import Dict, List

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique
from src.mglockne_story_line.llm.critiques.critique_result import CritiqueResult
from src.mglockne_story_line.story.event_sequence.elements.entity import Entity
from src.mglockne_story_line.util.entity_util import get_entity_categories


class CheckThatDifferentNamedEntitiesHaveDifferentNamesAsPreviousNamedEntitiesCritique(BaseCritique):
    """
    Make sure that a renamed named entity does not have the same name as an already existing named entity.
    """
    def process(self, values: Dict) -> CritiqueResult:
        known_entities: Dict[str, Entity] = {
            entity.name: entity
            for entity_type in get_entity_categories()
            for entity in values[entity_type]
        }

        # Conflict with existing entities
        duplicate_entities_with_previous: List[Dict] = []
        for entity_type in get_entity_categories():
            new_entity_names: List[Dict] = values[f'corrected_{entity_type}_name']
            for ent_name in new_entity_names:
                if ent_name['name'] in known_entities:
                    duplicate_entities_with_previous.append(ent_name)

        if len(duplicate_entities_with_previous) == 0:
            return CritiqueResult.correct(self.name)
        else:
            error_message: str = "Some of the entity names you provided match existing named entities. Please ensure these conflicts are avoided."
            error_message += f'\nThe following entities are already included in the list of known entities:\n'

            used_names = set()
            for ent_name in duplicate_entities_with_previous:
                if ent_name['name'] not in used_names:
                    used_names.add(ent_name['name'])
                    error_message += f' - "{ent_name["name"]}" (old name: "{ent_name["old_name"]}")\n'
            return CritiqueResult(self.name, False, duplicate_entities_with_previous, error_message)

    def __init__(self):
        super().__init__('fixed-names-disjunct-with-previous-critique')