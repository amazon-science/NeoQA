
from typing import List, Dict

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.timelines.event_sequence.modules.fictive_entities.entity_name_heuristics import \
    get_forbidden_char_critique_text_for, get_forbidden_chars, has_forbidden_char
from data_gen.util.entity_util import get_location_fields


class EntryFieldFormatHeuristics(BaseCritique):
    """
    Applies some heuristics of how the named entities where populated to avoid common problems we spotted.
    """
    def __init__(self, field_entity: str, name: str, selector: str, entity_type: str):
        super().__init__(name)
        self.field_entity: str = field_entity
        self.entity_type: str = entity_type
        self.selector: str = selector

    def to_error_string(self, ent: Dict):
        return f' - [{self.entity_type}; ID="{ent["id"]}"] {ent["name"]}: The value "{ent[self.field_entity]}" of the property "{self.field_entity}".\n'

    def process(self, values: Dict) -> CritiqueResult:
        errors: List[Dict] = []
        forbidden_chars: str = ', '.join(['"' + c + '"' for c in get_forbidden_chars(self.entity_type)])
        conflict_message: str = f"Change the following properties of these entities, ensuring they do not include these characters: {forbidden_chars}.\n"
        if self.field_entity in get_location_fields():
            conflict_message += get_forbidden_char_critique_text_for('location')

        entities: List[Dict] = values[self.selector]
        for ent in entities:
            conflict_properties: List[str] = []
            if self.field_entity in ent:
                if has_forbidden_char(ent[self.field_entity], self.entity_type):
                    conflict_properties.append(f'{ent[self.field_entity]}')

            if len(conflict_properties) > 0:
                conflict_message += f'{self.to_error_string(ent)}\n'
                errors.append({
                    'key': self.field_entity,
                    'obj': ent,
                    'type': self.entity_type
                })

        self.add_errors_to_result(values, errors)

        return CritiqueResult(
            self.name,
            len(errors) == 0,
            errors,
            conflict_message
        )
