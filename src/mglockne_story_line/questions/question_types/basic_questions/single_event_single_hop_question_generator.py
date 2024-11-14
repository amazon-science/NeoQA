from typing import Dict, List, Iterable, Optional

from src.mglockne_story_line.llm.modules.named_module_pipeline import NamedModulePipeline
from src.mglockne_story_line.questions.elements.qa_pair import QAPair
from src.mglockne_story_line.questions.question_generator import QuestionGenerator
from src.mglockne_story_line.util.entity_util import get_prev_snapshot_entity_xml, get_entity_categories
from src.mglockne_story_line.util.ids import generate_id
from src.mglockne_story_line.util.story_tools import remove_ids_from


class SingleEventQuestionGenerator(QuestionGenerator):

    def get_other_info(self) -> Dict:
        return self.status

    def on_start(self):
        self.status = {
            'discarded': []
        }

    def on_qa_pairs_generated(self, values: Dict):
        super().on_qa_pairs_generated(values)
        for qa in values.get('DISCARDED_QA_PAIRS', []):
            self.status.append(qa | {
                'created_at': values['CREATED_AT'],
                'used_evidence': values['EVIDENCE_CURRENT_SELECTIONS']
            })

    VAL_QUESTION: str = 'SINGLE_EV_QUESTION'
    VAL_ANSWER: str = 'SINGLE_EV_ANSWER'
    VAL_EVIDENCE_IDS: str = 'SINGLE_EV_EVIDENCE_IDS'
    VAL_HOPS: str = 'NUM_HOPS'
    VAL_CREATED_AT: str = 'CREATED_AT'

    def __init__(self,
                 name: str, evidence_selection_module: NamedModulePipeline,
                 question_answer_generation_module: NamedModulePipeline,
                 validate_modules: List[NamedModulePipeline],
                 unescape_outline: bool = True,
                 log_directory: Optional[str] = None,
                 question_refine_module: Optional[NamedModulePipeline] = None
                 ):
        super().__init__(
            name,
            evidence_selection_module,
            question_answer_generation_module,
            validate_modules,
            log_directory,
            question_refine_module=question_refine_module
        )
        self.unescape_outline: bool = unescape_outline
        self.status = None

    def _iterate_storyline(self, storyline: Dict) -> Iterable[Dict]:
        for i in range(len(storyline['events'])):
            entity_snapshot: Dict = storyline['elements']['snapshots'][i]
            event: Dict = storyline['events'][i]
            assert event['created_at'] == entity_snapshot['created_at']
            yield {
                'genre': storyline['genre'],
                'event': event,
                'entity_snapshot': entity_snapshot,
            }

    def _to_qa_pair(self, qa_data: Dict, validation_results: List[Dict], is_valid: bool, values: Dict, storyline: Dict) -> QAPair:
        distractors: List[Dict] = qa_data[QuestionGenerator.VAL_CURRENT_PAIR].get('distractors', [])
        return QAPair(
            question=qa_data[QuestionGenerator.VAL_CURRENT_PAIR][SingleEventQuestionGenerator.VAL_QUESTION],
            question_id=generate_id(qa_data[QuestionGenerator.VAL_CURRENT_PAIR]),
            answer=qa_data[QuestionGenerator.VAL_CURRENT_PAIR][SingleEventQuestionGenerator.VAL_ANSWER],
            evidence_ids=[qa_data[QuestionGenerator.VAL_CURRENT_SELECTION]],
            created_at=qa_data[SingleEventQuestionGenerator.VAL_CREATED_AT],
            num_hops=values[SingleEventQuestionGenerator.VAL_HOPS],
            is_valid=is_valid,
            category='single-event-single-hop',
            validations=validation_results,
            event_information={
                k: storyline[k] for k in ['event_type', 'event_type_id', 'story_seed_id']
            },
            distractors=distractors
        )

    def _get_values_for_current_storyline_subset(self, current_storyline_subset: Dict, storyline: Dict) -> Dict:

        outline_items: List[str] = []
        for item in current_storyline_subset['event']['outline']:
            sent: str = item['sentence']
            sent_id: str = item['id']
            if self.unescape_outline:
                sent = remove_ids_from(sent)
            outline_items.append(
                f'<item><id>{sent_id}</id><text>{sent}</text></item>'
            )

        prev_used_entities: Dict = get_prev_snapshot_entity_xml(
            storyline, current_storyline_subset['event']['created_at'], current_storyline_subset['event'],
            include_entity_updates=False
        )
        prev_used_entities_xml = '\n'.join([
            f'<{ent}>\n{prev_used_entities[ent]}\n</{ent}>'
            for ent in get_entity_categories()
        ])
        return {
            'OUTLINE': '\n'.join(outline_items),
            SingleEventQuestionGenerator.VAL_CREATED_AT: current_storyline_subset['event']['created_at'],
            'PREV_USED_ENTITIES_XML': prev_used_entities_xml,
        }