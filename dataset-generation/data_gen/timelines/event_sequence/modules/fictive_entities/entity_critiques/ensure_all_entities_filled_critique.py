from typing import Dict, List

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.util.entity_util import get_entity_categories
from data_gen.util.misc import find_by_props


class EnsureAllEntitiesFilledCritique(BaseCritique):

    """
    Double-checks by name and ID that all new entities have been filled.
    """

    def process(self, values: Dict) -> CritiqueResult:
        missing: List[Dict] = []
        for entity_type in get_entity_categories():
            filled_entities: List[Dict] = values[f'fictional_new_{entity_type}s']
            new_entities: List[Dict] = values[f'corrected_{entity_type}_name']

            for new_ent in new_entities:
                match = find_by_props(filled_entities, {'name': new_ent['name']})
                if match is None:
                    missing.append(new_ent)

        if len(missing) > 0:
            error_message: str = 'The following named entities are missing from your output (You are NOT allowed to change the entity name!). Please provide detailed information for these named entities, following the instructions above:\n'
            for ent in missing:
                error_message += f' - [ID={ent["id"]}] "{ent["name"]}" \n'
            return CritiqueResult(self.name, False, missing, error_message)
        else:
            return CritiqueResult.correct(self.name)

