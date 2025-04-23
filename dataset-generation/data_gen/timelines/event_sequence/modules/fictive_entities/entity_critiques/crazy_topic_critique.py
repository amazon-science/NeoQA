from typing import Dict, List

from data_gen.llm.critiques.base_critique import BaseCritique
from data_gen.llm.critiques.critique_result import CritiqueResult


class CrazyTopicCritique(BaseCritique):
    """
    Critique ensures that the outline does not contain any of the blacklisted words.
    """

    def __init__(self, key: str, field_type: str):
        super().__init__('crazy-topics')
        self.key: str = key
        self.field_type: str = field_type
        self.lower: bool = True

        self.forbidden_words: List[str] = [
            'galactic', 'planetary'
        ]

    def process(self, values: Dict) -> CritiqueResult:
        text: str = self._get_text(values)
        if self.lower:
            text = text.lower()

        critique_command: str = 'Please draft a new outline and avoid covering the following themes and topics: '
        forbidden_topics: List[str] = []
        for w in self.forbidden_words:
            if w in text:
                forbidden_topics.append(w)

        forbidden_topics_str: str = ', '.join([f'"{w}"' for w in forbidden_topics])
        critique_command += forbidden_topics_str

        return CritiqueResult(
            'crazy-topics',
            len(forbidden_topics) == 0,
            [{'found': w} for w in forbidden_topics],
            critique_command
        )

    def _get_text(self, values: Dict):
        to_check = values[self.key]
        if self.field_type == 'list':
            text: str = '\n'.join(to_check)
        else:
            raise ValueError(self.field_type)

        return text.strip()