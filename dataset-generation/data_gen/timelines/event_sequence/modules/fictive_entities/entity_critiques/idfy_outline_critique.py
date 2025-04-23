from typing import Dict, List, Set

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult
from data_gen.timelines.event_sequence.elements.entity import Entity
from data_gen.util.entity_util import get_entity_categories
from data_gen.util.misc import remove_obj_with_field_value
from data_gen.util.xml_util import dict_to_xml


class IdfyOutlineCritique(BaseCritique):
    """
    Heuristically check if the outline contains named entties that are not resoved.
    This critique is not enforced, allowing the LLM to ignore it to avoid errors from this heuristic result in wrong alignments.
    """

    def process(self, values: Dict) -> CritiqueResult:
        missing_ids: List[Dict]  = []
        text = ' '.join(values['story_item'])
        for entity_type in get_entity_categories():
            used_entities: List[Dict] = values[f'used-name-and-id-for-{entity_type}']
            for entity in used_entities:
                key : str = f'|{entity["id"]}' + '}'
                if key not in text:
                    missing_ids.append(entity)

        if len(missing_ids) == 0:
            return CritiqueResult.correct(self.name)
        else:
            self.num_errors += 1
            error_message: str = f'Please make sure to identify all mentions of the entities listed among those used in the outline. The following entities have not yet been found::\n'
            for ent in missing_ids:
                error_message += f' - [ID={ent["id"]}] Full name: "{ent["name"]}".\n'
            error_message += 'For each of these entities, check if they are explicitly referred to by name in the outline. If they are, tag them using the format {[phrase][entity-id]}.\n'
            error_message += 'DO NOT change the names of other entities in the outline to match any of the missing entities. If you cannot find some of the missing entities, simply ignore them.'
            return CritiqueResult(self.name, False, missing_ids, error_message)

    def __init__(self, name: str, remove_entities_after_errors: int):
        super().__init__(name)
        self.remove_entities_after_errors: int = remove_entities_after_errors
        self.num_errors: int = 0

    def reset(self):
        self.num_errors = 0

    def update_values(self, values: Dict, critique_results: List[CritiqueResult]) -> Dict:

        # Check if the outline masks entities that have not been selected as used
        values_updated: bool = False
        text = ' '.join(values['story_item'])
        for entity_type in get_entity_categories():
            for new_ent in values[f'corrected_{entity_type}_name']:
                key: str = f'|{new_ent["id"]}' + '}'
                entity_in_used: bool = len([e for e in values[f'used-name-and-id-for-{entity_type}'] if e['id'] == new_ent['id']]) > 0
                if key in text and not entity_in_used:
                    values[f'used-name-and-id-for-{entity_type}'].append({
                        'category': entity_type, 'id': new_ent['id'], 'name': new_ent['name']
                    })
                    values[f'used_{entity_type}'].append({'id': new_ent['id'], 'name': new_ent['name']})
                    values[f'used_new-{entity_type}'].append({
                        'category': entity_type, 'id': new_ent['id'], 'name': new_ent['name']
                    })
                    values_updated = True
            for existing_ent in values[entity_type]:
                key: str = f'|{existing_ent.entity_id}' + '}'
                entity_in_used: bool = len([e for e in values[f'used-name-and-id-for-{entity_type}'] if e['id'] == existing_ent.entity_id]) > 0
                if key in text and not entity_in_used:
                    values[f'used-name-and-id-for-{entity_type}'].append({
                        'category': entity_type, 'id': existing_ent.entity_id, 'name': existing_ent.name
                    })
                    values[f'used_{entity_type}'].append({'id': existing_ent.entity_id, 'name': existing_ent.name})
                    values[f'used_pre-existing-{entity_type}'].append(existing_ent)
                    values_updated = True

        if len(critique_results) > 0 and self.num_errors >= self.remove_entities_after_errors:
            assert len(critique_results) == 1
            values_updated = True
            critique_result: CritiqueResult = critique_results[0]

            # Remove entities from new entities if they have been new
            for entity_type in get_entity_categories():
                non_matched_entities: List[Dict] = [ent for ent in critique_result.errors if entity_type.upper() in ent['id']]
                for ent in non_matched_entities:
                    #values[f'new_{entity_type}_name'] = remove_obj_with_field_value(values[f'new_{entity_type}_name'], 'name', ent['name'])
                    values[f'corrected_{entity_type}_name'] = remove_obj_with_field_value(values[f'corrected_{entity_type}_name'], 'name', ent['name'])
                # Update XML
                # I believe we do not need them anymore, so remove to make sure
                values.pop(f'adjusted_{entity_type}s_xml', None)
                values.pop(f'new_{entity_type}_name', None)
                # values.pop(f'corrected_{entity_type}_name')

            # Remove entities from used entities
            for entity_type in get_entity_categories():
                non_matched_entities: List[Dict] = [ent for ent in critique_result.errors if entity_type.upper() in ent['id']]
                for ent in non_matched_entities:
                    values[f'used_{entity_type}'] = remove_obj_with_field_value(values[f'used_{entity_type}'], 'id', ent['id'])
                    values[f'used_new-{entity_type}'] = remove_obj_with_field_value(values[f'used_new-{entity_type}'], 'id', ent['id'])
                    values[f'used_pre-existing-{entity_type}'] = [e for e in values[f'used_pre-existing-{entity_type}'] if e.entity_id != ent['id']]
                    values[f'used-name-and-id-for-{entity_type}'] = remove_obj_with_field_value(values[f'used-name-and-id-for-{entity_type}'], 'id', ent['id'])

        if values_updated:
            # Update XML
            for entity_type in get_entity_categories():
                pre_existing_entities: List[Entity] = values[entity_type]
                used_entity_ids: Set[str] = set([e['id'] for e in values[f'used_{entity_type}']])
                pre_existing_entities = [e for e in pre_existing_entities if e.entity_id in sorted(list(used_entity_ids))]
                pre_existing_entity_ids: Set[str] = {e.entity_id for e in pre_existing_entities}
                new_entities = [e | {"category": entity_type} for e in values[f'used_{entity_type}'] if e['id'] not in pre_existing_entity_ids]
                values[f'all_used_{entity_type}_xml'] = '\n'.join(
                    [e.xml() for e in pre_existing_entities] + [f'<{e["category"]}>' + dict_to_xml(e) + f'</{e["category"]}>' for e in new_entities]
                )
                    # redo XML
        return values