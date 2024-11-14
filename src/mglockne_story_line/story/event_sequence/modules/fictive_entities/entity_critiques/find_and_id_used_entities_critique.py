from collections import defaultdict
from typing import Dict, List, Set

from src.mglockne_story_line.llm.critiques.base_critique import BaseCritique, CritiqueResult
from src.mglockne_story_line.story.event_sequence.elements.entity import Entity
from src.mglockne_story_line.util.entity_util import get_entity_categories
from src.mglockne_story_line.util.story_tools import is_substring_in_list


class FindUsedEntitiesCritique(BaseCritique):
    """
    This critique checks the outline after the named entity resolution via various heuristics:
    - Check if all named entities that occur in the outline are found at least once
    - Check that no other IDs exist or where hallucinated
    - Verify that no ID was clearly assigned incorrectly

    """
    def process(self, values: Dict) -> CritiqueResult:

        id_to_name_existing: Dict[str, Dict[str, str]] = defaultdict(dict)
        id_to_name_new: Dict[str, Dict[str, str]] = defaultdict(dict)

        for entity_type in get_entity_categories():
            existing_entities: List[Entity] = values[entity_type]
            for ent in existing_entities:
                assert ent.entity_id not in id_to_name_existing[entity_type]
                id_to_name_existing[entity_type][ent.entity_id] = ent.name
            for ent in values[f'corrected_{entity_type}_name']:
                assert ent['id'] not in id_to_name_new[entity_type]
                id_to_name_new[entity_type][ent['id']] = ent['name']

        # Combine
        id_to_name: Dict[str, Dict[str, str]] = dict()
        for entity_type in get_entity_categories():
            existing: Dict = id_to_name_existing[entity_type]
            added_new: Dict = id_to_name_new[entity_type]
            assert set(existing.keys()) & set(added_new.keys()) == set()
            id_to_name[entity_type] = existing | added_new


        #  Now verify
        missing_new_entities: List[Dict] = []
        mismatched_name_id_pairs: List[Dict] = []
        hallucinated_entities: List[Dict] = []
        missing_text_matched_entities: List[Entity] = []

        for entity_type in get_entity_categories():
            used_entities: List[Dict] = values[f'used_{entity_type}']

            # Check 1: Do ID and name match
            for ent in used_entities:
                if ent['id'] not in id_to_name[entity_type]:
                    hallucinated_entities.append(ent)
                else:
                    name: str = id_to_name[entity_type][ent['id']]
                    if name != ent['name']:
                        mismatched_name_id_pairs.append({
                            'id': ent['id'],
                            'name': ent['name'],
                            'real-name': name
                        })

            # Check 2: Do we have all the new entities?
            used_ids: Set[str] = {ent['id'] for ent in used_entities}
            new_entity_ids: Set[str] = set(id_to_name_new[entity_type].keys())
            for entity_id in sorted(list(new_entity_ids - used_ids)):
                missing_new_entities.append({
                    'id': entity_id, 'name': id_to_name_new[entity_type][entity_id]
                })


        # Check 3: Did we miss a entity?
        all_used_entity_names: List[str] = [
            ent['name']
            for entity_type in get_entity_categories()
            for ent in values[f'used_{entity_type}']
        ]

        # go over all entities and check if they exist in the outline but are not mentioned yet
        text: str = ' '.join(values['story_item'])
        for entity_type in get_entity_categories():
            for entity in values[entity_type]:
                # ignore entities if they are prt of a different entity (shallow heuristic, could be improved)
                if not is_substring_in_list(entity.name, all_used_entity_names):
                    if entity.name in text:
                        missing_text_matched_entities.append(entity)

        # Now check if we have errors
        errors: List[Dict] = []
        error_message: str = ''

        if len(missing_new_entities) > 0:
            errors.append({
                'name': 'missing', 'entities': missing_new_entities
            })
            error_message += f'Please ensure your response includes the following newly introduced entities: '
            error_message += ', '.join([f'"{ent["name"]} [ID={ent["id"]}]"' for ent in missing_new_entities])
            error_message += '\n\n'

        if len(mismatched_name_id_pairs) > 0:
            errors.append({
                'name': 'mismatched-ids', 'entities': mismatched_name_id_pairs
            })
            error_message += f'The following entities seem to have the wrong ID. Please double-check and correct either the assigned name or ID.:\n'
            for ent in mismatched_name_id_pairs:
                error_message += f' - [ID={ent["id"]}] You listed the name as "{ent["name"]}" but the correct name for this ID is "{ent["real-name"]}". \n'
            error_message += '\n'

        if len(hallucinated_entities) > 0:
            errors.append({
                'name': 'hallucinated-ids', 'entities': hallucinated_entities
            })
            error_message += f'The IDs for the following entities are unknown. Please ensure you only output entities from the provided lists.:\n'
            for ent in hallucinated_entities:
                error_message += f' - [ID={ent["id"]}] Name: "{ent["name"]}".\n'
            error_message += '\n'

        if len(missing_text_matched_entities) > 0:
            errors.append({
                'name': 'missing-matched-ids', 'entities': missing_text_matched_entities
            })
            error_message += f'The following entities appear in the outline but are missing from your response. Please make sure to include all entities from the provided lists that are mentioned in the outline.:\n'
            for ent in missing_text_matched_entities:
                error_message += f' - [ID={ent.entity_id}] Name: "{ent.name}".\n'
            error_message += '\n'

        if len(errors) == 0:
            return CritiqueResult.correct(self.name)
        else:
            return CritiqueResult(self.name, False, errors, error_message)
            # print(error_message)
            # assert False, 'for now to check'
            # return CritiqueResult(
            #     self.name, False, errors, error_message
            # )








        # Verify that all new entities have been identified