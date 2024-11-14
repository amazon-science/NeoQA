import random
from typing import List, Optional, Dict


class QAPair:
    def __init__(
            self,
            question: str,
            question_id: str,
            answer: Optional[str],
            evidence_ids: List[str],
            created_at: int,
            num_hops: int,
            is_valid: bool,
            category: str,
            validations: List[Dict],
            event_information: Dict,
            distractors: Optional[List[Dict]] = None,
            false_premise_category: Optional[str] = None,
            false_premise_sentence_id: Optional[str] = None,
            misc: Dict = None
    ):
        self.question: str = question
        self.question_id: str = question_id
        self.answer: Optional[str] = answer
        self.evidence_ids: List[str] = evidence_ids
        self.num_hops: int = num_hops
        self.is_valid: bool = is_valid
        self.validations: List[Dict] = validations
        self.created_at: int = created_at
        self.distractors: Optional[List[Dict]] = clean_distractors(distractors or [])
        self.misc: Dict = misc
        self.category = category
        self.false_premise_category = false_premise_category
        self.false_premise_sentence_id: str = false_premise_sentence_id
        self.event_information: Dict = event_information

    def __json__(self) -> Dict:
        distractor_answers: List[str] = self._make_distractor_answers()
        return {
            'question': self.question,
            'question_id': self.question_id,
            'evidence_ids': self.evidence_ids,
            'answer': self.answer,
            'num_hops': self.num_hops,
            'created_at': self.created_at,
            'category': self.category,
            'validation': {
                'is_valid': self.is_valid,
                'validations': self.validations,
            },
            'distractors': self.distractors,
            'distractor_answers': distractor_answers,
            'gold_answer_idx': distractor_answers.index(self.answer) if len(distractor_answers) > 0 else -1,
            'false_premise_category': self.false_premise_category,
            'false_premise_sentence_id': self.false_premise_sentence_id,
            'misc': self.misc,
            'event_information': self.event_information
        }

    def _make_distractor_answers(self) -> List[str]:
        if self.distractors is None or len(self.distractors) == 0:
            return []
        else:
            distractor_text: List[str] = [d['answer'] for d in self.distractors]
            if self.answer in distractor_text:
                pass
            else:
                pass
            assert self.answer not in distractor_text

            all_answers: List[str] = [self.answer] + distractor_text
            random.shuffle(all_answers)
            return all_answers

def clean_distractors(distractors: List[Dict]):
    cleaned_distractors: List[Dict] = []
    for distractor in distractors:
        assert 'answer' in distractor
        if distractor['distractor-sentences'] is None:
            distractor['distractor-sentences'] = []
        if isinstance(distractor['distractor-sentences'], str):
            sentences: List[str] = [sent_id.strip() for sent_id in distractor['distractor-sentences'].split(',')]
            sentences = [sent_id for sent_id in sentences if len(sent_id) >= 5]
            distractor['distractor-sentences'] = sentences
        cleaned_distractors.append(distractor)
    return cleaned_distractors
