import json
from copy import deepcopy
from typing import List, Dict, Optional

from src.mglockne_story_line.util.entity_util import get_all_property_fields
from src.mglockne_story_line.util.xml_util import dict_to_xml


class EntityUpdate:
    def __init__(self, created_at: int, event_update: str, date: str):
        self.created_at: int = created_at
        self.event_update: str = event_update
        self.date: str = date

    def copy(self):
        return EntityUpdate(self.created_at, self.event_update[:], self.date[:])

    def __str__(self):
        return json.dumps(self.json(), indent=2)

    def json(self) -> Dict:
        return {
            'created_at': self.created_at,
            "event_update": self.event_update,
            "date": self.date
        }

    def __json__(self) -> Dict:
        return self.json()


class Entity:
    def __init__(self, entity_class: str, name: Optional[str], description: Optional[str], type_of: Optional[str], properties: Dict, history: List[EntityUpdate], created_at: int, entity_id: str, last_updated_at: str):
        self.name: str = name
        self.entity_class: str = entity_class
        self.last_updated_at: str = last_updated_at
        self.description: str = description
        self.type_of: str = type_of
        self.properties: Dict = properties
        self.history: List[EntityUpdate] = history
        self.complete: bool = self.validate_completeness()
        self.created_at: int = created_at
        self.entity_id: str = entity_id

    @classmethod
    def create_new(cls, entity_class: str, values: Dict, node_idx: int, entity_id: str, last_updated_at: str):
        return Entity(
            entity_class,
            values.get('name', None),
            values.get('description', None),
            values.get('type', None),
            {k: values[k] for k in values.keys() if k in get_all_property_fields(entity_class)},
            [],
            node_idx,
            entity_id,
            last_updated_at
        )

    def change_properties(self, new_properties: Dict):
        self.name = new_properties.get('name')
        self.description = new_properties.get('description')
        self.type_of = new_properties.get('type', None)

        self.properties = {k: new_properties[k] for k in new_properties.keys() if k not in ['name', 'description', 'type', 'event_update', 'old_name']},

        if len(self.history) != 1:
            raise ValueError(f'Cannot only update new entities! (history={len(self.history)})')
        self.history[0].event_update = new_properties['event_update']

    def update(self, event_update: str, date: str, created_at: int, properties: Dict):
        self.history.append(EntityUpdate(created_at, event_update, date))
        if 'name' in properties:
            self.name = properties['name']
        if 'description' in properties:
            self.name = properties['description']
        if 'type' in properties:
            self.type_of = properties['type']

        for key in properties:
            if key in get_all_property_fields(self.entity_class):
                self.properties[key] = properties[key]
        self.last_updated_at: date

    def __json__(self) -> Dict:
        return self.json()

    def json(self) -> Dict:
        out = {
            **{
                'id': self.entity_id,
                'name': self.name,
                'entity_class': self.entity_class,
                'description': self.description,
                'type': self.type_of,
                'created_at': self.created_at,
                'last_updated': self.last_updated_at,
                'history': [hist.json() for hist in self.history]
              },
            **self.properties
        }
        return out

    def xml(self) -> str:
        props = {
            **{
                'id': self.entity_id, 'entity_class': self.entity_class, 'last_updated': self.last_updated_at,
                'name': self.name, 'description': self.description, 'type': self.type_of, 'created_at': self.created_at, 'history': self._history_xml()
            }, **self.properties,
        }
        return f'<{self.entity_class}>{dict_to_xml(props)}</{self.entity_class}>'


    def last_update_xml(self) -> str:
        update: str = self.history[-1].event_update
        props = {
            **{
                'id': self.entity_id, 'entity_class': self.entity_class, 'last_updated': self.last_updated_at,
                'name': self.name, 'description': self.description, 'type': self.type_of, 'created_at': self.created_at, 'update': update
            }, **self.properties,
        }
        return f'<{self.entity_class}>{dict_to_xml(props)}</{self.entity_class}>'

    def idfy_last_update(self, properties: Dict):
        assert properties['id'] == self.entity_id
        if 'description' in properties:
            self.description = properties['description']
        if 'update' in properties:
            self.history[-1].event_update = properties['update']

        for field in get_all_property_fields(self.entity_class):
            if field in properties:
                self.properties[field] = properties[field]

    def _history_xml(self) -> str:
        return ''.join([f'<event>{hist.date}: {hist.event_update}</event>' for hist in self.history])

    def validate_completeness(self) -> bool:
        is_valid: bool = True
        for field in [
            self.name, self.description, self.type_of
        ]:
            if field is None or len(field.strip()) == 0:
                is_valid = False
        return is_valid

    def __str__(self):
        return json.dumps(self.json(), indent=2)

    def copy(self):
        return Entity(
            self.entity_class[:],
            self.name[:],
            self.description[:],
            self.type_of[:] if self.type_of is not None else None,
            deepcopy(self.properties),
            [ev.copy() for ev in self.history],
            self.created_at,
            self.entity_id,
            self.last_updated_at
        )