from typing import List, Dict, Optional

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult


class ObjectListPropertyCritique(BaseCritique):
    """
    Ensures that a filled entity object includes all required properties.
    """

    def __init__(self, name: str, selector: str, properties: List[str], field_id: str = 'id', field_name: Optional[str] = 'name'):
        super().__init__(name)
        self.selector: str = selector
        self.properties: List[str] = properties
        self.field_id: str = field_id
        self.field_name: str = field_name

    def process(self, values: Dict) -> CritiqueResult:
        objects: List[Dict] = values[self.selector]
        errors: List[Dict] = []
        num_missing_ids: int = 0
        for obj in objects:
            missing_props = [prop for prop in self.properties if prop not in obj]
            if self.field_id not in obj:
                num_missing_ids += 1
            if len(missing_props) > 0:
                errors.append({
                    'obj': obj, 'missing_props': missing_props
            })

        if num_missing_ids == 0 and len(errors) == 0:
            return CritiqueResult.correct(self.name)
        else:
            error_message: str = ''
            if num_missing_ids > 0:
                error_message += f'Always include the ID property <{self.field_id}>! \n\n'
            if len(errors) > 0:
                error_message += f'The following properties are missing. Please ensure all properties are filled in:\n'
                for err in errors:
                    obj_id: str = err['obj'].get(self.field_id, '<missing ID>')
                    obj_name: str = err['obj'].get(self.field_name, '<missing name>')
                    obj_identifier: str = f'[ID={obj_id}; Name="{obj_name}"]' if self.field_name is not None else f'[ID={obj_id}]'
                    error_message += f' - {obj_identifier} Missing properties: {", ".join(err["missing_props"])} \n'

            if num_missing_ids > 0:
                errors += [{'num-missing-id': num_missing_ids}]
            return CritiqueResult(self.name, False, errors, error_message)
