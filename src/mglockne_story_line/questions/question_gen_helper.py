from typing import Dict, Iterable, List, Optional

from src.mglockne_story_line.util.entity_util import get_outline_dict_with_full_entity_names
from src.mglockne_story_line.util.story_tools import sort_outline_ids


def iterate_event_combinations(storyline: Dict, include_single_events: bool = True) -> Iterable[Dict]:

    events: List[Dict] = sorted(storyline['events'], key=lambda x: x['created_at'])
    all_combinations: List = []
    for start_idx in range(len(events) - 1):
        subsets: List[Dict] = [{
            'created_at': [events[start_idx]['created_at'], events[end_idx]['created_at']],
            'genre': storyline['genre'],
            'events': [events[start_idx], events[end_idx]],
            'storyline': storyline,
            'entity_snapshots': storyline['elements']['snapshots'],
            } for end_idx in range(start_idx + 1, len(events))
        ]


        if include_single_events:
            subsets.append({
                'created_at': [events[start_idx]['created_at']],
                'genre': storyline['genre'],
                'events': [events[start_idx]],
                'storyline': storyline,
                'entity_snapshots': storyline['elements']['snapshots'],
            })
        all_combinations.extend(subsets)

    # Add last
    if include_single_events:
        all_combinations.append({
            'created_at': [events[-1]['created_at']],
            'genre': storyline['genre'],
            'events': [events[-1]],
            'storyline': storyline,
            'entity_snapshots': storyline['elements']['snapshots'],
        })

    yield from all_combinations


def get_outline_dict_for_events(events: List[Dict], entity_snapshots: List[Dict]) -> Dict:
    outline_dict: Dict[str, Dict] = dict()
    for event in events:
        created_at: int = event['created_at']
        snapshots: List[Dict] = [snapshot for snapshot in entity_snapshots if snapshot['created_at'] == created_at]
        if len(snapshots) != 1:
            raise ValueError(f'Expected to find exactly one snapshot with "created_at={created_at}" but found {len(snapshots)}.')
        snapshot: Dict = snapshots[0]
        event_outline_dict: Dict = get_outline_dict_with_full_entity_names(event['outline'], snapshot['entities'])
        assert len(set(event_outline_dict.keys()) & set(outline_dict.keys())) == 0
        outline_dict |= event_outline_dict
    return outline_dict

def make_sentence_xml(sentence_id: str, outline_dict: Dict, use_key: str = 'decoded_sentence_corrected'):
    return f'<item><id>{sentence_id}</id><text>{outline_dict[sentence_id][use_key]}</text></item>'

def get_selected_sentence_xml(sentence_ids: List[str], outline_dict: Dict) -> str:
    return '\n'.join(list(map(lambda sent_id: make_sentence_xml(sent_id, outline_dict), sentence_ids)))

def get_xml_event(event: Dict, outline_dict: Dict, use_key: str = 'decoded_sentence_corrected'):
    outline_items: List[str] = []
    outline_ids: List[str] = list(sort_outline_ids([item['id'] for item in event['outline']]))
    for outline_id in outline_ids:
        outline_items.append(make_sentence_xml(outline_id, outline_dict, use_key=use_key))
    content = '\n'.join(outline_items)
    event_xml: str = f'<event>\n<date>{event["date"]}</date>\n<content>\n{content}\n</content>\n</event>'
    return event_xml


def get_xml_event_selection(event: Dict, outline_ids: List[str], outline_dict: Dict, use_key: str = 'decoded_sentence_corrected'):
    outline_items: List[str] = []
    outline_ids: List[str] = list(sort_outline_ids(outline_ids))
    for outline_id in outline_ids:
        outline_items.append(f'<sentence>{outline_dict[outline_id][use_key]}</sentence>')
    content = '\n'.join(outline_items)
    event_xml: str = f'<date>{event["date"]}</date>\n<content>\n{content}\n</content>'
    return event_xml


def get_xml_for_events(
        all_events: List[Dict], outline_dict: Dict, cut_event_with_selection: Optional[List[Dict]] = None, use_key: str = 'decoded_sentence_corrected'
):
    cut_event_with_selection = cut_event_with_selection or []
    sorted_events: List[Dict] = sorted(all_events, key=lambda ev: ev['created_at'])
    if len(cut_event_with_selection) > 0:
        max_created_at: int = get_max_created_at(cut_event_with_selection)
        sorted_events = [ev for ev in sorted_events if ev['created_at'] <= max_created_at]

    event_xml: str = '\n'.join([
        get_xml_event(event, outline_dict, use_key=use_key) for event in sorted_events
    ])
    return event_xml


def get_max_created_at(selected_events: List[Dict]) -> int:
    return max([ev['created_at'] for ev in selected_events])
