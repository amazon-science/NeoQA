import random
from copy import deepcopy
from typing import Dict, Union, List, Optional, Iterable, Set
from data_gen.llm.modules.named_module_pipeline import NamedModulePipeline
from data_gen.questions.elements.qa_pair import QAPair
from data_gen.questions.question_gen_helper import iterate_event_combinations, get_outline_dict_for_events, \
    get_selected_sentence_xml, get_xml_for_events
from data_gen.questions.question_generator import QuestionGenerator
from data_gen.questions.question_reviser import QuestionReviser
from data_gen.util.entity_util import entity_id_to_outline_items_from_events, get_prev_snapshot_entity_xml, \
    get_entity_categories, get_all_entity_names
from data_gen.util.ids import generate_id
from data_gen.util.story_tools import sort_outline_ids


class MultiEventMultiHopBridgeEntityQuestionGenerator(QuestionGenerator):

    def _to_qa_pair(self, qa_data: Dict, validation_results: List[Dict], is_valid: bool, values: Dict,
                    storyline: Dict) -> QAPair:

        distractors: List[Dict] = qa_data[QuestionGenerator.VAL_CURRENT_PAIR].get('distractors', [])
        evidence_ids = list(sort_outline_ids(
            list(set(qa_data[QuestionGenerator.VAL_CURRENT_SELECTION] + qa_data[QuestionGenerator.VAL_CURRENT_PAIR]['additional_sentence_ids']))
        ))
        additional_evidence_id_explanation: Dict = {
            k: qa_data[QuestionGenerator.VAL_CURRENT_PAIR][k] for k in [
                'additional_sentence_ids', 'additional_sentence_explanation'
            ]
        }
        return QAPair(
            question=qa_data[QuestionGenerator.VAL_CURRENT_PAIR][MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_QUESTION],
            question_id=generate_id(qa_data[QuestionGenerator.VAL_CURRENT_PAIR]),
            answer=qa_data[QuestionGenerator.VAL_CURRENT_PAIR][MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_ANSWER],
            evidence_ids=evidence_ids,
            created_at=qa_data[MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_CREATED_AT],
            num_hops=len(evidence_ids),
            is_valid=is_valid,
            category='multi-multi-hop-bridge',
            validations=validation_results,
            event_information = {
                k: storyline[k] for k in ['event_type', 'event_type_id', 'story_seed_id']
            },
            distractors=distractors,
            misc={
                'additional_sent': additional_evidence_id_explanation,
                'use_decoded': 'corrected'
            }
        )

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

    VAL_QUESTION: str = 'MULTI_HOP_BRIDGE_QUESTION'
    VAL_ANSWER: str = 'MULTI_HOP_BRIDGE_ANSWER'
    VAL_EVIDENCE_IDS: str = 'MULTI_HOP_BRIDGE_EVIDENCE_IDS'
    VAL_HOPS: str = 'NUM_HOPS'
    VAL_CREATED_AT: str = 'CREATED_AT'

    def __init__(self,
                 name: str, evidence_selection_module: NamedModulePipeline,
                 question_answer_generation_module: NamedModulePipeline,
                 validate_modules: List[NamedModulePipeline],
                 question_revisers: Optional[List[QuestionReviser]] = None,
                 log_directory: Optional[str] = None,
                 question_refine_module: Optional[NamedModulePipeline] = None,
                 include_single_events: bool = True,
                 min_entity_counts: int = 2,
                 max_entities_per_selection: Optional[int] = None,
                 sample_num_entities: bool = False,
                 max_entity_per_selection_random_seed: int = 1
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
        self.min_entity_counts: int = min_entity_counts
        self.max_entities_per_selection: Optional[int] = max_entities_per_selection
        #self.max_entity_per_selection_random_seed: int = max_entity_per_selection_random_seed
        self.sample_num_entities: bool = sample_num_entities
        random.seed(max_entity_per_selection_random_seed)

    def _iterate_storyline(self, storyline: Dict) -> Iterable[Dict]:

        for event in storyline['events']:
            entity_id_to_outline_mentions: Dict[str, List[str]] = entity_id_to_outline_items_from_events(
                [event], storyline['elements']['snapshots']
            )
            event['entity_id_to_outline_ids'] = entity_id_to_outline_mentions

        all_subsets: List[Dict] = []

        for subset in iterate_event_combinations(storyline, self.include_single_events):
            # Collect all possibilities where we have multiple entities across all events.

            candidates: List[Dict] = list(self._iterate_named_entity_candidates(subset))
            if self.max_entities_per_selection is not None:
                random.shuffle(candidates)

                current_max_entities: int = self.max_entities_per_selection
                if self.sample_num_entities:
                    current_max_entities = random.randint(1, self.max_entities_per_selection)

                candidates = candidates[:current_max_entities]

            for named_entity_candidate in candidates:
                all_subsets.append(deepcopy(subset | named_entity_candidate))
                #yield subset | named_entity_candidate
        yield from all_subsets

    def _iterate_named_entity_candidates(self, subset: Dict) -> Iterable[Dict]:
        if len(subset['events']) == 1:
            # Need to find entities that appear twice at least
            for entity_id in subset['events'][0]['entity_id_to_outline_ids']:
                if len(subset['events'][0]['entity_id_to_outline_ids'][entity_id]) > 1:
                    yield {
                    'bridge_entity_id': entity_id
                }
        else:
            assert len(subset['events']) == 2
            # shared_entity_ids: List[str] = sorted(
            #     list(set(subset['events'][0]['entity_id_to_outline_ids']) & set(subset['events'][1]['entity_id_to_outline_ids']))
            # )

            ids_event_1 = {
                k for k in subset['events'][1]['entity_id_to_outline_ids']
                if len(subset['events'][1]['entity_id_to_outline_ids'][k]) >= self.min_entity_counts
            }
            ids_event_0 = {
                k for k in subset['events'][1]['entity_id_to_outline_ids'] if
                len(subset['events'][0]['entity_id_to_outline_ids'][k]) >= self.min_entity_counts
            }
            shared_entity_ids = sorted(list(ids_event_1 & ids_event_0))

            for entity_id in shared_entity_ids:
                yield {
                    'bridge_entity_id': entity_id
                }

    def on_evidence_selected(self, current_storyline_subset: Dict, selection: Dict, values: Dict) -> Dict:
        outline_dict: Dict = get_outline_dict_for_events(current_storyline_subset['events'], current_storyline_subset['entity_snapshots'])
        values['SELECTED_SENTENCES'] = get_selected_sentence_xml(selection['sentence_ids'], outline_dict)
        values['SELECTION_EXPLANATION'] = selection.get('explanation', '')
        return values

    def _get_values_for_current_storyline_subset(self, current_storyline_subset: Dict, storyline: Dict) -> Dict:

        selected_events: List[Dict] = current_storyline_subset['events']
        all_events: List[Dict] = storyline['events']
        bridge_entity_names: List[str] = get_all_entity_names(
            current_storyline_subset['bridge_entity_id'], [
                snapshot for snapshot in current_storyline_subset['entity_snapshots']
                if snapshot['created_at'] in {ev['created_at'] for ev in selected_events}
            ]
        )

        bridge_entity_refer_name: str = bridge_entity_names[0]
        if len(bridge_entity_names) > 1:
            assert len(bridge_entity_names) == 2
            bridge_entity_refer_name += f' (alternatively: "{bridge_entity_names[1]}")'

        outline_dict: Dict = get_outline_dict_for_events(
            all_events, current_storyline_subset['entity_snapshots']
        )

        max_created_at: int = max([ev['created_at'] for ev in selected_events])
        all_events_to_date_xml: str = get_xml_for_events(all_events, outline_dict, cut_event_with_selection=selected_events)
        selected_events_xml: str = get_xml_for_events(selected_events, outline_dict, cut_event_with_selection=None)

        latest_event: Dict = sorted(selected_events, key= lambda ev: ev['created_at'])[-1]
        assert latest_event['created_at'] == max_created_at
        prev_used_entities: Dict = get_prev_snapshot_entity_xml(
            storyline, max_created_at, latest_event, include_entity_updates=False
        )
        prev_used_entities_xml = '\n'.join([
            f'<{ent}>\n{prev_used_entities[ent]}\n</{ent}>'
            for ent in get_entity_categories()
        ])

        return {
            'OUTLINES': selected_events_xml,
            'STORYLINE_OUTLINE_TO_DATE': all_events_to_date_xml,
            'SELECTED_EVENTS': selected_events,
            "BRIDGE_ENTITY_NAME": bridge_entity_refer_name,
            "BRIDGE_ENTITY_ID": current_storyline_subset['bridge_entity_id'],
            'KNOWN_PREV_NAMED_ENTITIES': prev_used_entities_xml,
            'OUTLINE_DICT': outline_dict,
            MultiEventMultiHopBridgeEntityQuestionGenerator.VAL_CREATED_AT: max_created_at
        }