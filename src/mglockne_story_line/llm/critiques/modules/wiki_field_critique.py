from typing import List, Dict, Optional

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
from src.mglockne_story_line.llm.verifiers.base_verifier import BaseVerifier, VerifyResult
from src.mglockne_story_line.llm.verifiers.core_verifiers.wikipedia_verifier import WikiApiEntityFlaggerPool


class WikiFieldCritique(BaseCritique):
    """
    Ensures that the value at a given field is distinct to known Wikipedia entries.
    """
    def __init__(self, field_entity: str, name: str, selector: str, entity_type: str):
        super().__init__(name)
        self.field_entity: str = field_entity
        self.verifier: BaseVerifier = WikiApiEntityFlaggerPool.get(should_check_text=False)
        self.entity_type: str = entity_type
        self.selector: str = selector

    def to_error_string(self, ent: Dict):
        out: str =  f'<{self.entity_type}>{ent[self.field_entity]}</{self.entity_type}>'
        # if self.field_entity == 'name' and len(ent[self.field_entity].split(' ')) == 1:
        #     out += f' (Consider adding a second word to the name.)'
        return out

    def process(self, values: Dict) -> CritiqueResult:
        errors: List[Dict] = []
        conflict_message: str = f'The following entities have conflicting properties that match existing Wikipedia pages. Please resolve these conflicts, ensuring that the entities are distinct. Update the outline to reflect these changes.\n'

        entities: List[Dict] = values[self.selector]
        for ent in entities:
            conflict_properties: List[str] = []
            if self.field_entity in ent:
                res: VerifyResult = self.verifier.check_entity(ent[self.field_entity])
                if len(res.errors) > 0:
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


class CustomWikiFieldCritique(WikiFieldCritique):
    def to_error_string(self, ent: Dict):
        name: Optional[str] = ent.get('name', None)
        if name is not None:
            identifier = f'"{name}"'
        else:
            identifier = f'ID="{ent["entity_id"]}"' # was id
        err: str = f'[{self.entity_type}] {identifier}: The value of the property {self.field_entity} ("{ent[self.field_entity]}") exists on Wikipedia. Change the value for "{self.field_entity}!"'
        err += '\nFix these errors and return the corrected answer using the same XML format as before.'
        return err

    def __init__(self, field_entity: str, name: str, selector: str, entity_type: str):
        super().__init__(field_entity, name, selector, entity_type)