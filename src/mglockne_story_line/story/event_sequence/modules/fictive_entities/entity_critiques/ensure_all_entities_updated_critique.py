import json
from idlelib.iomenu import errors
from typing import Dict, List

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
from src.mglockne_story_line.util.entity_util import get_entity_categories
from src.mglockne_story_line.util.misc import find_by_props


class EnsureAllEntitiesUpdatedCritique(BaseCritique):

    """
    Double-checks by name and ID that all new entities have been filled.
    """

    def process(self, values: Dict) -> CritiqueResult:
        missing: List[Dict] = []
        for entity_type in get_entity_categories():
            used_entities: List[Dict] = values[f'used-name-and-id-for-{entity_type}']
            updated_entities: List[Dict] = values[f'tmp_{entity_type}_updates']

            for used_ent in used_entities:
                match = find_by_props(updated_entities, {'entity_id': used_ent['id']})
                if match is None:
                    missing.append(used_ent)

        if len(missing) > 0:
            # print('MISSING:')
            # print(json.dumps(missing, indent=2))
            error_message: str = 'Please ensure you provide updates for all specified entities. You forgot to update the following entities::\n'
            for ent in missing:
                error_message += f' - [ID={ent["id"]}] Name: "{ent["name"]}" \n'
            print(error_message)
            return CritiqueResult(self.name, False, errors, error_message)
        else:
            return CritiqueResult.correct(self.name)