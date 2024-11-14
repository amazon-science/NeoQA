from copy import deepcopy
from typing import List, Dict

from src.mglockne_story_line.story.entity_storing.entity_snapshot import EntitySnapshot
from src.mglockne_story_line.story.event_sequence.elements.entity import Entity
from src.mglockne_story_line.util.entity_util import get_entity_categories


class EntityStore:
    def __init__(self, entity_types: List[str] = None):
        self.snapshots: List[EntitySnapshot] = []
        self.next_ids: Dict[str, int] = {
            entity_type: 1 for entity_type in entity_types or get_entity_categories()
        }

    def get_next_ids_dict(self) -> Dict[str, int]:
        return deepcopy(self.next_ids)

    def add_new_snapshot(self, entities: Dict[str, List[Entity]], date: str, timestep: int):
        assert len(self.snapshots) == 0 or self.snapshots[-1].timestep == timestep - 1
        self.snapshots.append(EntitySnapshot(timestep, date, entities))

    def get_last_snapshot(self) -> EntitySnapshot:
        return self.snapshots[-1].copy_entities()

    def __json__(self):
        return {
            'next_ids': self.next_ids,
            'snapshots': self.snapshots
        }