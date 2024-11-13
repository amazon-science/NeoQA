import re
from os import listdir
from os.path import join
from typing import Dict, List, Iterable

from data_gen.timelines.event_sequence.elements.entity import Entity
from data_gen.util.entity_util import get_entity_categories


def clean_evidence_ids(evidence_ids: List[str]) -> List[str]:
    return sort_outline_ids(list(set([
        evidence_id.replace('[', '').replace(']', '') for evidence_id in evidence_ids
    ])))


def to_entity_dict(entities: Dict[str, List[Entity]]) -> Dict[str, Dict[str, Entity]]:
    return {
        key: {
            ent.name.lower().strip(): ent for ent in entities[key]
        } for key in get_entity_categories()
    }


def sort_outline_ids(unsorted_ids: Iterable[str]) -> List[str]:
    def sort_pos(_id: str) -> int:
        return int(_id.split('-')[1][1:])
    return sorted(unsorted_ids, key=sort_pos)


def update_entities(values: Dict) -> List[Dict]:
    entity_dict: Dict[str, Dict[str, Entity]] = to_entity_dict(values)
    used_entities: List[Dict] = []
    for entity_type in get_entity_categories():
        for update in values[f'{entity_type}_updates']:
            entity_name: str = update['name'].lower().strip()
            entity_update: str = update['update']
            ent: Entity = entity_dict[entity_type][entity_name]
            ent.update(entity_update, values['date'], values['created_at'])
            used_entities.append({
                'name': update['name'], 'entity_type': entity_type, 'new': ent.created_at == values['created_at']
            })
    return used_entities


def renew_outline(values: Dict) -> Dict:
    values['outline'] = '\n'.join(
        values['story_item']
    )
    return values


def remove_ids_from(text: str) -> str:
    pattern: re.Pattern = re.compile(r'\{([^|]+)\|([A-Z]+-\d+,?)+\}')
    matches = re.finditer(pattern, text)
    for match in matches:
        text = text.replace(match.group(0), match.group(1))
    return text


def is_substring_in_list(substring: str, items: List[str]) -> bool:
    for item in items:
        if substring in item:
            return True
    return False


def create_history_xml(date: str, story_items: List[str], remove_ids: bool = False) -> str:
    outline: str = ' '.join(story_items)
    if remove_ids:
        outline = remove_ids_from(outline)
    return f'<event><date>{date}</date><outline>{outline}</outline></event>'


def create_history_xml_from_event(event) -> str:
    return create_history_xml(event.date, event.outline)


def find_entity(name: str, entities: List[Entity]):
    for ent in entities:
        if ent.name == name:
            return ent
    raise ValueError(f'Could not find entity with name = "{name}"!')


def update_changed_entity(values: Dict, new_entity: Dict, key: str) -> Dict:
    old_name: str = new_entity.pop('old_name')
    old_entity: Entity = find_entity(old_name, values[key])
    old_entity.change_properties(new_entity)
    return values


def get_outline_directory_from_story_path(story_path: str):
    subdirectories = [d for d in listdir(story_path) if d not in ['questions', 'news']]
    assert len(subdirectories) == 1, subdirectories
    return join(story_path, subdirectories[0])


def get_all_storyline_directories(base_dir: str):
    for story in listdir(base_dir):
        yield get_outline_directory_from_story_path(join(base_dir, story))
