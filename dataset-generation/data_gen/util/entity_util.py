import re
from collections import defaultdict
from copy import deepcopy
from typing import List, Dict, Set

from data_gen.util.xml_util import dict_to_xml


def remove_ids_from(text: str) -> str:
    pattern: re.Pattern = re.compile(r'\{([^|]+)\|([A-Z]+-\d+,?)+\}')
    matches = re.finditer(pattern, text)
    for match in matches:
        text = text.replace(match.group(0), match.group(1))
    return text


def get_entity_categories() -> List[str]:
    return [
        'person', 'organization', 'location', 'product', 'art', 'building', 'event', 'miscellaneous'
    ]


def get_entity_category_from_id(assumed_entity_category: str, entity_id: str) -> str:
    category: str =  entity_id.split('-')[0].lower().strip()
    assert category in get_entity_categories(), category
    if category != assumed_entity_category:
        print(f'Correcting the entity type for {entity_id} (previous "{assumed_entity_category}")')
    return category


def get_entity_fields(entity_type: str) -> List[str]:
    type_to_entity_properties = {
        'location': ['country'],
        'person': ['nationality', 'spouse'],
        'organization': ['headquarters'],
        'product': ['manufacturer'],
        'art': ['creator', 'current_location_country', 'current_location_city', 'current_location_place'],
        'building': ['place', 'city', 'country', 'architect'],
        'event': ['place', 'city', 'country', 'organizer'],
        'miscellaneous': [],
    }
    return type_to_entity_properties[entity_type]


def get_location_fields() -> Set[str]:
    return {
        'country', 'location', 'headquarters', 'place', 'city', 'country', 'current_location_country', 'current_location_city', 'current_location_place'
    }


def get_all_property_fields(entity_type: str) -> List[str]:
    type_to_entity_properties = {
        'location': ['country', 'population', 'area', 'founded' 'climate', 'elevation', 'country'],
        'person': [
            'nationality', 'spouse', 'date_of_birth', 'gender', 'profession', 'education','weight',
            'height', 'eye_color', 'hair_color', 'political_affiliation', 'marital_status'
        ],
        'organization': ['headquarters', 'founded', 'industry', 'mission_statement', 'number_of_employees', 'annual_revenue'],
        'product': ['manufacturer', 'release_date', 'price', 'weight', 'warranty'],
        'art': ['creator', 'current_location', 'year_created'],
        'building': ['location', 'architect', 'year_built', 'height', 'floors', 'material', 'capacity'],
        'event': ['location', 'organizer', 'date', 'duration', 'number_of_participants', 'budget'],
        'miscellaneous': [],
    }
    return type_to_entity_properties[entity_type]


def get_entity_by_id(entities: List, entity_id: str, allow_missing: bool = False):
    for ent in entities:
        if ent.entity_id == entity_id:
            return ent
    if allow_missing:
        return None

    raise ValueError(f'No entity with ID={entity_id}!')


def get_flat_id_to_entity(entities_dict: Dict[str, List[Dict]]):
    return {
        ent['id']: ent
        for entity_type in get_entity_categories()
        for ent in entities_dict[entity_type]
    }


def entity_id_to_outline_items(id2ent: Dict[str, Dict], outline: List[Dict]) -> Dict[str, List[str]]:
    out: Dict[str, List[str]] = defaultdict(list)
    for entity_id in id2ent.keys():
        for item in outline:
            if f'|{entity_id}' + '}' in item['sentence']:
                out[entity_id].append(item['id'])
    return out


def get_prev_snapshot_entity_xml(story: Dict, index: int, event: Dict, include_entity_updates: bool=False) -> Dict:
    if index == 0:
        return {ent: '' for ent in get_entity_categories()}
    xml_entities_from_before: Dict = {
        entity_type: get_xml_entities(
            story['elements']['snapshots'][index - 1]['entities'][entity_type],
            event['created_at'],
            [
                ent for ent in event['used_entities'] if ent['entity_type'] == entity_type
            ],
            include_entity_updates
        ) for entity_type in get_entity_categories()
    }
    return xml_entities_from_before


def get_xml_entity_snapshot(snapshot: Dict, used_entities: List[Dict], include_history: bool = False) -> str:
    assert not include_history, 'Change the -1 to the actual created_at if enable'
    entities: List[str] = [
        f'<{ent_type}>\n{get_xml_entities(snapshot[ent_type], -1, used_entities)}\n</{ent_type}>' for ent_type in get_entity_categories()
    ]
    return '\n'.join(entities)


def get_xml_entities(entities: List[Dict], created_at: int, used_entities: List[Dict], include_history: bool = True) -> str:
    used_ids: Set[str] = {
        e['id'] for e in used_entities
    }
    entities = [
        deepcopy(ent) for ent in entities if ent['id'] in used_ids
    ]

    for ent in entities:
        if include_history:
            ent['history'] = [
                hist for hist in ent['history'] if hist['created_at'] <= created_at
            ]
        else:
            ent.pop('history')

    return '\n'.join([
        dict_to_xml(ent) for ent in entities
    ])


def get_outline_dict_with_full_entity_names(outline: List[Dict], entity_snapshot: Dict) -> Dict[str, Dict]:
    entity_dict: Dict[str, Dict] = {
        entity['id']: entity
        for entity_type in get_entity_categories()
        for entity in entity_snapshot[entity_type]
    }

    pattern: re.Pattern = re.compile(r'\{([^|]+)\|([A-Z]+-\d+,?)+\}')
    result: Dict = dict()
    for item in outline:
        decoded_sentence: str = item['sentence'][:]
        used_entities: List[str] = []
        matches = re.finditer(pattern, decoded_sentence)

        addon_information: Set[str] = set()
        for match in matches:
            _id = match.group(2)
            full_name: str = entity_dict[_id]['name']
            used_entities.append(_id)
            decoded_sentence = decoded_sentence.replace(match.group(0), full_name)

            # these are the heuristics to consider a name flawed
            if len(full_name.split(' ')) > 7:
                addon_information.add(full_name)

        if len(addon_information) > 0:
            # we have a noisy name
            decoded_sentence_full = remove_ids_from(item['sentence'])
            extra_details: str = '; '.join(sorted(list(addon_information)))
            decoded_sentence_full += f' ({extra_details})'
        else:
            decoded_sentence_full = decoded_sentence

        result[item['id']] = {
            'sentence': item['sentence'],
            'decoded_sentence': decoded_sentence,
            'decoded_sentence_full': decoded_sentence_full,
            'entity_ids': sorted(used_entities),
            'has_entity_name_conflict': decoded_sentence != decoded_sentence_full
        }
    return result



def get_all_entity_names(entity_id: str, entity_snapshots: List[Dict]) -> List[str]:
    names = set()
    for snapshot in entity_snapshots:
        entity_dict: Dict[str, Dict] = {
            entity['id']: entity
            for entity_type in get_entity_categories()
            for entity in snapshot['entities'][entity_type]
        }
        names.add(entity_dict[entity_id]['name'])
    return sorted(list(names))


def entity_id_to_outline_items_from_events(events: List[Dict], entity_snapshots: List[Dict]) -> Dict[str, List[str]]:

    def find_snapshot(_event: Dict) -> Dict:
        for snapshot in entity_snapshots:
            if snapshot['created_at'] == event['created_at']:
                return snapshot
        assert False

    entity_id_to_outline_mentions: Dict[str, List[str]] = defaultdict(list)
    for event in events:
        snapshot: Dict = find_snapshot(event)
        id2ent: Dict[str, Dict] = get_flat_id_to_entity(snapshot['entities'])
        current_entity_id_to_outline_mentions: Dict[str, List[str]] = entity_id_to_outline_items(id2ent, event['outline'])
        for key in current_entity_id_to_outline_mentions:
            entity_id_to_outline_mentions[key].extend(current_entity_id_to_outline_mentions[key])
    return entity_id_to_outline_mentions


class EntityIdProvider:
    def __init__(self, next_ids: Dict[str, int]):
        self.next_ids = next_ids

    def get_id(self, entity_type: str):
        if entity_type not in self.next_ids:
            raise ValueError(f'Could not find "{entity_type}" in {self.next_ids.keys()}!')
        next_id: str = f'{entity_type.upper()}-{self.next_ids[entity_type]}'
        self.next_ids[entity_type] += 1
        return next_id

    def export(self) -> Dict[str, int]:
        return deepcopy(self.next_ids)

