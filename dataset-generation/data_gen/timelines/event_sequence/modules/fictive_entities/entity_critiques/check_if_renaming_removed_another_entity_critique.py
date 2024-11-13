from typing import Dict, List


# 09.12
from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.util.entity_util import get_entity_categories


class CheckIfRenamingRemovedAnotherEntityCritique(BaseCritique):

    def __init__(self, name: str, ignore_after: int):
        super().__init__(name)
        self.num_errors: int = 0
        self.ignore_after: int = ignore_after

    def process(self, values: Dict) -> CritiqueResult:
        if self.num_errors >= self.ignore_after:
            return CritiqueResult.correct(self.name)
        else:
            new_named_entities: List[Dict] = [
                ent
                for entity_type in get_entity_categories()
                for ent in values[f'corrected_{entity_type}_name']
            ]

            text: str = ' '.join(values['story_item']).lower()

            missing_new_named_entities: List[Dict] = []
            for ent in new_named_entities:
                updated_ent_name: str = ent['name'].lower()
                if updated_ent_name not in text:
                    missing_new_named_entities.append(ent)

            if len(missing_new_named_entities) == 0:
                return CritiqueResult.correct(self.name)
            else:
                self.num_errors += 1
                missing_new_named_entities = sorted(list(missing_new_named_entities), key=lambda x: x['name'])

                message = 'It seems that after renaming, the following named entities are missing from the outline. Please ensure that you only rename the specified entities and that all other named entities remain present in the outline.'
                for ent in missing_new_named_entities:
                    message += f'\n - {ent["name"]}'

                return CritiqueResult(self.name, False, missing_new_named_entities, message)



    def reset(self):
        self.num_errors = 0