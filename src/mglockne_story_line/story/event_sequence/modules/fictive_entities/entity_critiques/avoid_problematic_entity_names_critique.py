from collections import defaultdict
from typing import Dict, List

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
from src.mglockne_story_line.story.event_sequence.modules.fictive_entities.entity_name_heuristics import has_forbidden_char, get_forbidden_char_critique_text_for
from src.mglockne_story_line.util.entity_util import get_entity_categories


class AvoidProblematicEntityNamesCritique(BaseCritique):
    """
    Uses some heuristics to avoid certain problems of how named entities may get renamed when making them disjoint from
    Wikipedia.
    For example, we do not allow "," in location names as this leads to "City, Country" names, merging various named
    entities, which can easily interfere  with other named entities in the outline.
    """

    def process(self, values: Dict) -> CritiqueResult:
        error_entities: Dict[str, List] = defaultdict(list)
        for entity_type in get_entity_categories():
            new_entity_names: List[str] = values[f'new_{entity_type}_name']
            for ent_name in new_entity_names:
                if has_forbidden_char(ent_name, entity_type):
                    error_entities[entity_type].append(ent_name)

        if len(error_entities.values()) == 0:
            return CritiqueResult.correct(self.name)
        else:
            error_message_base: str = ''
            errs: List[Dict] = []
            for entity_type in error_entities:
                if len(error_entities[entity_type]) > 0:
                    error_message_base += get_forbidden_char_critique_text_for(entity_type)
                for entity_name in error_entities[entity_type]:
                    error_message_base += f' - [{entity_type}] "{entity_name}" \n'
                    errs.append({'name': entity_name})
            return CritiqueResult(self.name, False, errs, error_message_base)

    def __init__(self, max_word_count: int = 5):
        super().__init__('entity-name-heuristics-critique')
        self.max_word_count: int = max_word_count
