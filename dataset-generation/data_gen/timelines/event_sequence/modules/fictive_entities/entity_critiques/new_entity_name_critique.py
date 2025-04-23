from typing import Dict, List

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.timelines.event_sequence.elements.entity import Entity
from data_gen.util.entity_util import get_entity_categories


class NewEntityNameCritique(BaseCritique):
    def process(self, values: Dict) -> CritiqueResult:
        known_entities: Dict[str, Entity] = {
            entity.name: entity
            for entity_type in get_entity_categories()
            for entity in values[entity_type]
        }
        duplicate_entities: List[Entity] = []
        for entity_type in get_entity_categories():
            new_entity_names: List[str] = values[f'new_{entity_type}_name']
            for ent_name in new_entity_names:
                if ent_name in known_entities:
                    duplicate_entities.append(known_entities[ent_name])

        if len(duplicate_entities) == 0:
            return CritiqueResult.correct(self.name)
        else:
            error_message: str = "Some of the new entities you've identified already exist within the known entities. Please compare the found entity names with those listed in <entities> and provide a complete list of new entity names, excluding those already present in <entities>."
            error_message += f'\nThe following entities are already included in the list of known entities:\n'

            used_names = set()
            for entity in duplicate_entities:
                if entity.name not in used_names:
                    used_names.add(entity.name)
                    error_message += f' - [{entity.entity_class}] "{entity.name}"\n'
            return CritiqueResult(self.name, False, [ent.json() for ent in duplicate_entities], error_message)

    def __init__(self, name: str):
        super().__init__(name)