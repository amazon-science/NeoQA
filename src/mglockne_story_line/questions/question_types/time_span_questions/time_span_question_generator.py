from typing import Dict, List, Iterable, Optional, Union

from src.mglockne_story_line.llm.modules.named_module_pipeline import NamedModulePipeline

from src.mglockne_story_line.questions.elements.qa_pair import QAPair
from src.mglockne_story_line.questions.question_gen_helper import iterate_event_combinations, \
    get_outline_dict_for_events, get_selected_sentence_xml, get_xml_for_events, get_max_created_at

from src.mglockne_story_line.questions.question_generator import QuestionGenerator
from src.mglockne_story_line.questions.question_reviser import QuestionReviser
from src.mglockne_story_line.util.ids import generate_id


class MultiEventTimeSpanQuestionGenerator(QuestionGenerator):

    def add_selection_values(self, selection_values: Dict, current_selection: Union[Dict, List]) -> Dict:
        return super().add_selection_values(selection_values, current_selection['sentence_ids'])

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

    VAL_QUESTION: str = 'TIMESPAN_QUESTION'
    VAL_ANSWER: str = 'TIMESPAN_ANSWER'
    VAL_EVIDENCE_IDS: str = 'TIMESPAN_EVIDENCE_IDS'
    VAL_HOPS: str = 'NUM_HOPS'
    VAL_CREATED_AT: str = 'CREATED_AT'

    def __init__(self,
                 name: str, evidence_selection_module: NamedModulePipeline,
                 question_answer_generation_module: NamedModulePipeline,
                 validate_modules: List[NamedModulePipeline],
                 question_revisers: Optional[List[QuestionReviser]] = None,
                 log_directory: Optional[str] = None,
                 question_refine_module: Optional[NamedModulePipeline] = None,
                 include_single_events: bool = True
                 ):
        super().__init__(
            name=name,
            evidence_selection_module=evidence_selection_module,
            question_answer_generation_module=question_answer_generation_module,
            validate_modules=validate_modules,
            log_directory=log_directory,
            question_revisers=question_revisers,
            question_refine_module=question_refine_module
        )
        self.status = None
        self.unescape_outline: bool = True
        self.include_single_events : bool = include_single_events

    def _iterate_storyline(self, storyline: Dict) -> Iterable[Dict]:
        all_subsets = list(iterate_event_combinations(storyline, self.include_single_events))
        yield from all_subsets

    def on_evidence_selected(self, current_storyline_subset: Dict, selection: Dict, values: Dict) -> Dict:
        outline_dict: Dict = get_outline_dict_for_events(current_storyline_subset['events'], current_storyline_subset['entity_snapshots'])
        values['SELECTED_SENTENCES'] = get_selected_sentence_xml(selection['sentence_ids'], outline_dict)
        values['SELECTION_EXPLANATION'] = selection.get('explanation', '')
        return values


    def _to_qa_pair(self, qa_data: Dict, validation_results: List[Dict], is_valid: bool, values: Dict, storyline: Dict)-> QAPair:
        distractors: List[Dict] = qa_data[QuestionGenerator.VAL_CURRENT_PAIR].get('distractors', [])
        evidence_ids: List[str] = sorted(list(set(
            qa_data[QuestionGenerator.VAL_CURRENT_SELECTION] + qa_data['QA_CURRENT_PAIR']['ADDITIONAL_SENTENCE_IDS']
        )))

        return QAPair(
            question=qa_data[QuestionGenerator.VAL_CURRENT_PAIR][MultiEventTimeSpanQuestionGenerator.VAL_QUESTION],
            question_id=generate_id(qa_data[QuestionGenerator.VAL_CURRENT_PAIR]),
            answer=qa_data[QuestionGenerator.VAL_CURRENT_PAIR][MultiEventTimeSpanQuestionGenerator.VAL_ANSWER],
            evidence_ids=evidence_ids,
            created_at=qa_data[MultiEventTimeSpanQuestionGenerator.VAL_CREATED_AT],
            num_hops=len(evidence_ids),
            is_valid=is_valid,
            category='multi-event-time-span',
            validations=validation_results,
            event_information={
                k: storyline[k] for k in ['event_type', 'event_type_id', 'story_seed_id']
            },
            distractors=distractors,
            misc={
                'scratchpad': qa_data[QuestionGenerator.VAL_CURRENT_PAIR]['scratchpad'],
                'scratchpad2': qa_data[QuestionGenerator.VAL_CURRENT_PAIR]['scratchpad2'],
                'previous_version': qa_data[QuestionGenerator.VAL_CURRENT_PAIR]['current_qa_pair1'],
                'use_decoded': 'corrected'
            }
        )

    def _get_values_for_current_storyline_subset(self, current_storyline_subset: Dict, storyline: Dict) -> Dict:

        selected_events: List[Dict] = current_storyline_subset['events']
        all_events: List[Dict] = storyline['events']

        outline_dict: Dict = get_outline_dict_for_events(
            all_events, current_storyline_subset['entity_snapshots']
        )


        all_events_to_date_xml: str = get_xml_for_events(all_events , outline_dict, cut_event_with_selection=selected_events)
        selected_events_xml: str = get_xml_for_events(selected_events , outline_dict, cut_event_with_selection=None)

        return {
            'OUTLINES': selected_events_xml,
            'STORYLINE_OUTLINE_TO_DATE': all_events_to_date_xml,
            'SELECTED_EVENTS': selected_events,
            MultiEventTimeSpanQuestionGenerator.VAL_CREATED_AT: get_max_created_at(selected_events)
        }