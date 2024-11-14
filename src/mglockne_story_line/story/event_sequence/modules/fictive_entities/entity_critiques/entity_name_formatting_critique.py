import re
from typing import List, Dict, Tuple

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult


class EntityNameFormattingCritique(BaseCritique):
    """
    Ensures that the entity name is formatted appropriately to avoid that the entity is only unique due to some tricks.
    - Entity must not contain any brackets.
    """
    def __init__(self, field_entity: str, name: str, selector: str, entity_type: str):
        super().__init__(name)
        self.field_entity: str = field_entity
        self.tests: List[Tuple[re.Pattern, str]] = [
            (re.compile(r'.+\(.+\).*'), 'Must not contain abbreviations or similar specifications. Do not use brackets to add additional information.')
        ]
        self.selector: str = selector
        self.entity_type: str = entity_type

    def process(self, values: Dict) -> CritiqueResult:
        errors: List[Dict] = []
        conflict_message: str = f'The following entity names appear to violate the requirements.:\n'

        entities: List[Dict] = [e for e in values[self.selector] if len(e) > 0]
        for ent in entities:
            field: str = ent[self.field_entity]
            for pattern, err_msg in self.tests:
                if pattern.match(field):
                    errors.append({
                        'key': self.field_entity,
                        'obj': ent,
                        'type': self.entity_type,
                        'err': err_msg
                    })
                    conflict_message += f'<{self.entity_type}>{field}</{self.entity_type}> ({err_msg})\n'

        self.add_errors_to_result(values, errors)

        return CritiqueResult(
            self.name,
            len(errors) == 0,
            errors,
            conflict_message
        )