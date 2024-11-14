from typing import Dict, List, Tuple

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
from src.mglockne_story_line.util.entity_util import get_entity_categories


class MaxNameWordCountCritique(BaseCritique):
    def process(self, values: Dict) -> CritiqueResult:
        too_long_entity_names: List[Tuple[str, str]] = []
        for entity_type in get_entity_categories():
            new_entity_names: List[str] = values[f'new_{entity_type}_name']
            for ent_name in new_entity_names:
                num_words = len(ent_name.split(' '))

                if num_words > self.max_word_count:
                    too_long_entity_names.append((entity_type, ent_name))

        if len(too_long_entity_names) == 0:
            return CritiqueResult.correct(self.name)
        else:

            error_message: str = f"Please review the identified named entities to ensure they are indeed unique and clearly defined names. Keep in mind that a named entity should not exceed {self.max_word_count} words:\n"
            for entity_type, entity_name in too_long_entity_names:
                error_message += f' - [{entity_type}] "{entity_name}" \n'
            return CritiqueResult(self.name, False, [{'type': e_type, 'name': e_name} for e_type, e_name in too_long_entity_names], error_message)

    def __init__(self, max_word_count: int = 5):
        super().__init__('max-entity-word-count-critique')
        self.max_word_count: int = max_word_count