from typing import List, Optional

from data_gen.llm.get_llm import get_llm
from data_gen.llm.modules.named_module_pipeline import NamedModulePipeline
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.questions.generate_questions import generate_questions
from data_gen.questions.question_generator import QuestionGenerator
from data_gen.questions.question_types.false_premise.contradictory_premise_reviser import \
    ContradictoryFalsePremiseReviser
from data_gen.questions.question_types.false_premise.uncertain_false_premise_reviser import UncertainFalsePremiseReviser
from data_gen.questions.question_types.multi_hop_bridge.modules.multi_hop_bridge_question_distractor_module import \
    MultiHopBridgeQuestionDistractorModule
from data_gen.questions.question_types.multi_hop_bridge.modules.multi_hop_bridge_question_write_module import \
    MultiEventMultiHopQuestionWriteModule
from data_gen.questions.question_types.multi_hop_bridge.modules.multi_hop_bridge_sentence_selection_module import \
    MultiEventBridgeEntitySentenceSelectionModule
from data_gen.questions.question_types.multi_hop_bridge.multi_hop_bridge_question_generator import \
    MultiEventMultiHopBridgeEntityQuestionGenerator


def generate_multi_hop_bridge_questions(
    storyline_directories: List[str],
    llm_name: str,
    event_num: int = 10,
    max_num_evidence_selections: int = 1,  # otherwise we generate way too much
    min_entity_counts: int = 2,
    max_entities_per_selection: Optional[int] = 2,  # otherwise we generate way too much
    num_valid_questions_per_evidence_selection: int = 1,  # otherwise we generate way too much
    sample_num_entities: bool = False,
    num_distractors: int = 5
):
    """
    Generates multi-hop (2 hop) questions with a bridge named entity. In general the workflow is: For each combination of events:
    1. select a bridge named entity
    2. Select suitable evidence sentences
    3. Generate multi-hop questions
    4. Generate plausible distractors for multiple choice
    5. Generate contradictory false premise questions for each generated valid question
    6. Generate unknown false premise questions for each generated valid question

    :param max_num_evidence_selections      The maximum number of evidence sentences that will serve as basis to form a question (for each named entity in each event combination).
    :param min_entity_counts                Only consider named entities if they appear at least this many times in *each* selected event.
    :param max_entities_per_selection       If set, at most this many (randomly selected) named entities will be considered for each event combination.
    :param num_valid_questions_per_evidence_selection       For each selected pair of evidence sentences, this many valid questions will be generated.
    :num_distractors                        Number of plausible distractors.
    """

    llm_strict: BaseLLMWrapper = get_llm(llm_name, temperature=0.0, max_tokens=5000)

    question_generator: QuestionGenerator = MultiEventMultiHopBridgeEntityQuestionGenerator(
        'multiv2-bridge-series',   # was single-2hop-bridge-series.json
        evidence_selection_module=NamedModulePipeline(
            [
                MultiEventBridgeEntitySentenceSelectionModule(llm_strict, 'select', 'v1',  max_num_selections=max_num_evidence_selections)
            ], 'select-2hop-bridge'
        ),
        question_answer_generation_module=NamedModulePipeline(
            [
                MultiEventMultiHopQuestionWriteModule(llm_strict, 'create-question', 'v4'),  # was v3
            ], 'multi-event-2-hop-bridge-questions'
        ),
        validate_modules=[],
        question_refine_module=NamedModulePipeline(
            [
                MultiHopBridgeQuestionDistractorModule(llm_strict, 'create-distractors', 'v1')
            ], 'multi-event-distractors-2hop-bridge'
        ),
        question_revisers=[
            ContradictoryFalsePremiseReviser(
                llm_strict, 'contradictory-false-premise', 'v1', 'contradictory'),
            UncertainFalsePremiseReviser(
                llm_strict, 'uncertain-false-premise', 'v1', 'uncertain-specificity'
            )
        ],
        min_entity_counts=min_entity_counts,
        max_entities_per_selection=max_entities_per_selection,
        max_entity_per_selection_random_seed=123,
        sample_num_entities=sample_num_entities
    )

    generate_questions(
        generator=question_generator,
        storyline_directories=storyline_directories,
        storyline_file_name=f'EXPORT_it-{event_num}.json',
        values={
            'NUM_QUESTIONS': num_valid_questions_per_evidence_selection,  # How many questions are generated per evidence
            'NUM_DISTRACTORS': num_distractors  # How many distractors are generated per question
        }
    )
