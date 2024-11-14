from collections import defaultdict
from typing import Dict, List, Optional

from src.mglockne_story_line.story.event_sequence.elements.entity import Entity


class EntitySnapshot:
    """
    This stores all entities at a given timestep (int).
    Each event is associated with an entity at a given timestep (int).
    """
    def __init__(self, timestep: Optional[int], date: Optional[str], entities: Dict[str, List[Entity]]):
        self.entities: Dict[str, List[Entity]] = entities
        self.timestep: int = timestep
        self.date: str = date

    def copy_entities(self):
        new_entities:  Dict[str, List[Entity]] = defaultdict(list)
        for key in self.entities.keys():
            for ent in self.entities[key]:
                new_entities[key].append(ent.copy())
        return EntitySnapshot(None, None, new_entities)

    def __json__(self):
        return {
            'created_at': self.timestep,
            'date': self.date,
            'entities': self.entities
        }
