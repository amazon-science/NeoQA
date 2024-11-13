from typing import Optional, List, Dict

from data_gen.timelines.event_sequence.elements.entity import Entity
from data_gen.util.story_tools import to_entity_dict


class Continuation:
    def __init__(self, summary: str, last_date: str, continuation_date: str):
        self.summary: str = summary
        self.last_date: str = last_date
        self.continuation_date: str = continuation_date

    @classmethod
    def create(cls, summary: str, last_date: str, continuation_date: str) -> 'Continuation':
        return Continuation(
            summary, last_date, continuation_date
        )

    def __json__(self):
        return {
            'summary': self.summary,
            'last_date': self.last_date,
            'continuation_date': self.continuation_date,
        }

    def copy(self) -> 'Continuation':
        return Continuation(self.summary, self.last_date, self.continuation_date)


class Event:
    def __init__(
            self,
            created_at: int,
            summary: str,
            outline: List[str],
            used_entities: List[Dict],
            date: str,
            continuation: Continuation = None,
            parent: Optional['Event'] = None
    ):
        self.created_at: int = created_at
        self.summary: str = summary
        self.outline: List[str] = outline
        self.used_entities: List[Dict] = used_entities
        self.parent: Optional['Event'] = parent
        self.continuation: Continuation = continuation.copy()
        self.child: Optional['Event'] = None
        self.date: str = date

    def __json__(self):
        return {
            'created_at': self.created_at,
            'summary': self.summary,
            'outline': self.get_id_outline(),
            'used_entities': self.used_entities,
            'parent': self.parent.created_at if self.parent is not None else None,
            'continuation': self.continuation,
            'child': self.child,
            'date': self.date,
        }

    def get_id_outline(self) -> List[Dict]:
        return [{
            'sentence': sentence,
            'id': f'N{self.created_at}-S{pos}',
            'pos': pos
        } for pos, sentence in enumerate(self.outline)]

    def event_summary(self, entities: Dict[str, List[Entity]]):
        print(f'[NODE={self.created_at}, {self.date}] {self.summary}')
        print('[ENTITIES]')
        entity_dict = to_entity_dict(entities)
        for ent in self.used_entities:
            is_new: str = 'NEW' if ent['new'] else ''
            description: str = entity_dict[ent['entity_type']][ent['name'].lower()].description
            print(f'\t{is_new} [{ent["entity_type"]}] {ent["name"]}: {description}')

    def __str__(self):
        out: str = f'HEADLINE:\n{self.summary}\n\n'
        out += f'OUTLINE:\n'
        out += '\n'.join(self.outline)
        out += '\n\n'
        out += f'CONTINUATIONS:'
        out += f'HEADLINE::{self.continuation.summary}\n'
        return out

