import random
import shutil
from copy import deepcopy
from os.path import join, exists
from typing import List, Optional, Dict

from data_gen.llm.modules.module_pipeline import ModulePipeline
from data_gen.timelines.entity_storing.entity_snapshot import EntitySnapshot
from data_gen.timelines.entity_storing.entity_store import EntityStore
from data_gen.timelines.event_sequence.elements.entity import Entity
from data_gen.timelines.event_sequence.elements.event import Event, Continuation
from data_gen.util.entity_util import get_entity_categories
from data_gen.util.file_util import store_json
from data_gen.util.story_tools import create_history_xml_from_event


class EventSequence2:
    def __init__(
            self, name: str,
            output_directory: str,
            pipeline_init: ModulePipeline,
            pipeline_continue: ModulePipeline,
            genre: str,
            summary_init: str,
            story_seed_id: str,
            story_init_random_seed: int
    ):
        self.output_directory: str = join(output_directory, name)
        self.genre: str = genre
        self.summary_init: str = summary_init
        self.name: str = name
        self.entities: EntityStore = EntityStore()
        self.pipeline_init: ModulePipeline = pipeline_init
        self.pipeline_continue: ModulePipeline = pipeline_continue
        self.head_node: Optional[Event] = None
        self.created_at_idx: int = 0
        self.story_seed_id: str = story_seed_id
        self.story_init_random_seed: int = story_init_random_seed

    def start(
            self,
            args: Optional[Dict] = None,
            keywords: Optional[List[str]] = None
    ) -> Event:

        # Cleanup first
        if exists(self._get_output_directory_for_story()):
            shutil.rmtree(self._get_output_directory_for_story())

        if self.head_node is not None:
            raise ValueError('Cannot start a new event, old event exists!')

        random.seed(self.story_init_random_seed)
        args = args or dict()
        out = self.pipeline_init.execute(
            self._get_output_directory_for_story(),
            args | {
            'genre': self.genre,
            'histories': [],
            'event_summary': self.summary_init,
            'event_summary_for_name': self.summary_init[:20],
            'keywords': ', '.join(keywords or []),
            'created_at': self.created_at_idx,
            'next_ids': self.entities.get_next_ids_dict(),
            'provided_date': ''
        } | {
           entity_type: [] for entity_type in get_entity_categories()
        } | {
                f'{entity_type}s_xml': '' for entity_type in get_entity_categories()
            })
        out.pop('critique_errors', None)

        self._update_entities_with_values(out)

        outline: List[str] = out['story_item']
        used_entities: List[Dict] = out['used_entities']
        event: Event = Event(
            self.created_at_idx,
            self.summary_init,
            outline,
            used_entities,
            out['date'],
            out['continuation']
        )
        self.head_node = event
        self.created_at_idx += 1
        return event

    def continue_news(self, keywords: Optional[List[str]] = None) -> Event:
        most_recent_node: Event = self.head_of_branch()
        continuation: Continuation = most_recent_node.continuation

        last_snapshot: EntitySnapshot = self.entities.get_last_snapshot()
        entities: Dict[str, List[Entity]] = {entity_type: last_snapshot.entities[entity_type] for entity_type in get_entity_categories()}
        entities_xml: Dict[str, str] = dict()
        for entity_type in get_entity_categories():
            current_entities: List[str] = [ent.xml() for ent in entities[entity_type]]
            entities_xml[f'{entity_type}s_xml'] = '\n'.join(current_entities)

        out = self.pipeline_continue.execute(
            self._get_output_directory_for_story(),
            {
            'genre': self.genre,
            'event_summary': continuation.summary,
            'event_summary_for_name': continuation.summary[:20],
            'init_summary': self.summary_init,
            'keywords': ', '.join(keywords or []),
            'created_at': self.created_at_idx,
            'histories': self.create_histories(),
            'KEY_OUTLINE_REFINE_STEP': 0,
            'next_ids': self.entities.next_ids,
            'provided_date': continuation.continuation_date
        } | entities | entities_xml)

        outline: List[str] = out['story_item']
        continuation: Continuation = out['continuation']
        used_entities: List[Dict] = out['used_entities']

        event: Event = Event(
            self.created_at_idx,
            out['event_summary'],
            outline,
            used_entities,
            out['date'],
            continuation,
            parent=most_recent_node
        )

        most_recent_node.child = event
        self.created_at_idx += 1
        self._update_entities_with_values(out)
        return event

    def _update_entities_with_values(self, values: Dict):
        self.entities.add_new_snapshot(
            {k: values[k] for k in get_entity_categories()},
            values['date'],
            values['created_at']
        )
        next_ids: Dict[str, int] = values['next_ids']
        self.entities.next_ids = deepcopy(next_ids)

    def _get_output_directory_for_story(self) -> str:
        if self.genre is None or self.summary_init is None or self.story_seed_id is None:
            raise ValueError('Must start with "start()"')
        dir_name: str = f'{self.genre.upper()}_{self.story_seed_id}__{self.summary_init.replace(" ", "-")[:15]}'

        # Added for WIN (26.11)
        dir_name = dir_name.replace(':', '-')

        return join(self.output_directory, dir_name)

    def create_histories(self) -> List[str]:
        histories: List[str] = []
        node: Event = self.head_node
        while node is not None:
            histories.append(create_history_xml_from_event(node))
            node = node.child
        return histories

    def get_entities_as_xml(self, key: str) -> str:
        xml_entities: List[str] = [
            f'<{key}>{entity.xml()}</{key}>' for entity in self.entities[key] if entity.name is not None
        ]
        return '\n'.join(xml_entities)

    def head_of_branch(self):
        node = self.head_node
        while node.child is not None:
            node = node.child
        return node

    def get_all_nodes(self):

        nodes: List[Event] = [self.head_node]
        while nodes[-1].child is not None:
            nodes.append(nodes[-1].child)

        return nodes

    def export(self, name: str, additional_data: Optional[Dict] = None):
        events = [ev.__json__() for ev in self.get_all_nodes()]
        for ev in events:
            ev.pop('child')
        store_json({
            'genre': self.genre,
            'events': events,
            'elements': self.entities
        } | additional_data or dict(),
        join(self._get_output_directory_for_story(), 'EXPORT_' + name + '.json'), pretty=True)
