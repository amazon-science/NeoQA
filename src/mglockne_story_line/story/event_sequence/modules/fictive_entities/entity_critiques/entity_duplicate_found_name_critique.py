from typing import Dict, List

from spacy.tokens.doc import defaultdict

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
from src.mglockne_story_line.util.entity_util import get_entity_categories


class NewEntityNameFoundTwiceCritique(BaseCritique):
    """
    Triggers if the LLM detects the same named entity multiple times.
    """
    def process(self, values: Dict) -> CritiqueResult:

        name_to_entity_type: Dict[str, List[str]] = defaultdict(list)
        for entity_type in get_entity_categories():
            new_entity_names: List[str] = values[f'new_{entity_type}_name']
            for ent_name in new_entity_names:
                name_to_entity_type[ent_name.strip()].append(entity_type)

        duplicate_names: List[str] = [
            name for name in name_to_entity_type.keys() if len(name_to_entity_type[name]) > 1
        ]

        if len(duplicate_names) == 0:
            return CritiqueResult.correct(self.name)
        else:
            error_message: str = "You have identified several named entities more than once. Please choose the correct entity type for each one and list each entity only once under the appropriate type.>\n"
            for name in duplicate_names:
                entity_types: str = ', '.join([
                    f'<{t}>' for t in name_to_entity_type[name]
                ])
                error_message += f'The named entity "{name}" is listed as: {entity_types}'

            return CritiqueResult(self.name, False, [{name: name_to_entity_type[name]} for name in duplicate_names], error_message)

    def __init__(self):
        super().__init__('find-same-entity-as-different-types-critique')