from copy import deepcopy
from datetime import datetime
from os import makedirs
from os.path import join
from typing import List, Dict, Iterable, Optional, Union

from data_gen.llm.critiques.unified_critique_module import XMlParseError
from data_gen.llm.modules.named_module_pipeline import NamedModulePipeline
from data_gen.questions.elements.qa_pair import QAPair
from data_gen.questions.question_reviser import QuestionReviser
from data_gen.util.file_util import make_filename_safe


class QuestionGenerator:

    VAL_SELECTIONS: str = 'EVIDENCE_SELECTIONS'
    VAL_CURRENT_SELECTION: str = 'EVIDENCE_CURRENT_SELECTIONS'
    VAL_PAIRS: str = 'QA_PAIRS'
    VAL_CURRENT_PAIR: str = 'QA_CURRENT_PAIR'

    def __init__(
            self,
            name: str,
            evidence_selection_module: NamedModulePipeline,
            question_answer_generation_module: NamedModulePipeline,
            validate_modules: List[NamedModulePipeline],
            question_revisers: Optional[List[QuestionReviser]] = None,
            log_directory: Optional[str] = None,
            question_refine_module: Optional[NamedModulePipeline] = None
    ):
        self.name: str = name
        self.question_revisers: List[QuestionReviser] = question_revisers or []
        self.evidence_selection_module: NamedModulePipeline = evidence_selection_module
        self.question_answer_generation_module: NamedModulePipeline = question_answer_generation_module
        self.question_refine_module: Optional[NamedModulePipeline] = question_refine_module
        self.validate_modules: List[NamedModulePipeline] = validate_modules
        self.log_directory: str = log_directory or f'outputs/qa-generation/{name}/raw'
        makedirs(self.log_directory, exist_ok=True)
        self.generated_qa_pairs: List[QAPair] = []

    def generate(self, storyline: Dict, init_values: Optional[Dict] = None) -> Dict:
        self.on_start()
        init_values = init_values or dict()
        summary_name: str = make_filename_safe(storyline["events"][0]["summary"][:25])
        storyline_name: str = f'{storyline["genre"].upper()}__{summary_name}'
        self.generated_qa_pairs: List = []
        for idx, current_storyline_subset in enumerate(self._iterate_storyline(storyline)):
            self._generate_questions_for(
                idx,
                join(self.log_directory, storyline_name),
                current_storyline_subset,
                deepcopy(init_values),
                storyline
            )
        return {
            'questions': self.generated_qa_pairs,
            'generator': self.name,
            'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'generation_setup': {
                'select': {
                    'name': self.evidence_selection_module.name, 'modules': self.evidence_selection_module.get_content_versions()
                },
                'generate': {
                    'name': self.question_answer_generation_module.name,
                    'modules': self.question_answer_generation_module.get_content_versions()
                },
                'validate': [{
                    'name': val.name,
                    'modules': val.get_content_versions()
                } for val in self.validate_modules],
                'revisers': [{
                    'name': rev.output_key,
                    'question_generation_module': rev.question_generation_module.get_content_versions(),
                    'question_refine_module': rev.question_refine_module.get_content_versions() if rev.question_refine_module is not None else None,
                } for rev in self.question_revisers],
            },
            'others': self.get_other_info()
        }

    def get_file_name(self) -> str:
        return f'{self.name}.json'

    def get_other_info(self) -> Dict:
        return dict()

    def _iterate_storyline(self, storyline: Dict) -> Iterable[Dict]:
        raise NotImplementedError

    def _get_values_for_current_storyline_subset(self, current_storyline_subset: Dict, storyline: Dict) -> Dict:
        """
        Generates the values starting for the event.
        """
        raise NotImplementedError

    def on_qa_pairs_generated(self, values: Dict):
        pass

    def on_start(self):
        pass

    def _to_qa_pair(self, qa_data: Dict, validation_results: List[Dict], is_valid: bool, values: Dict, storyline: Dict) -> QAPair:
        raise NotImplementedError

    def on_evidence_selected(self, current_storyline_subset: Dict, selection: Dict, values: Dict) -> Dict:
        return values

    def add_selection_values(self, selection_values: Dict, current_selection: Union[Dict, List]) -> Dict:
        """
        Adjust the values for a current selection of evidence items. By default, it assumes that the current selection
        refers to the evidence IDs
        """
        selection_values[QuestionGenerator.VAL_CURRENT_SELECTION] = current_selection
        return selection_values

    def _generate_questions_for(self, subset_idx: int, directory: str, current_storyline_subset: Dict, init_values: Dict, storyline: Dict):
        try:
            values: Dict = self._get_values_for_current_storyline_subset(current_storyline_subset, storyline) | init_values
            values['subset_idx'] = subset_idx

            # Get eviden
            # ce selections
            print('YAAAY')
            selection_out: Dict = self.evidence_selection_module.execute(
                output_directory=directory,
                initial_status=deepcopy(values)
            )

            # Generate questions for each selected
            selections: List[Dict] = selection_out[QuestionGenerator.VAL_SELECTIONS]
            for idx, selection in enumerate(selections):
                selection_values: Dict = deepcopy(values)
                selection_values = self.on_evidence_selected(current_storyline_subset, selection, selection_values)
                selection_values['selection_idx'] = idx
                selection_values = self.add_selection_values(deepcopy(selection_values), selection)
                #selection_values[QuestionGenerator.VAL_CURRENT_SELECTION] = selection

                initial_status_qa_gen: Dict = selection_values
                if 'event' in current_storyline_subset:
                    selection_values |= {
                        'event': {
                            'outline': current_storyline_subset['event']['outline'],
                            'entities': current_storyline_subset['entity_snapshot']
                        }
                    }


                # These are the QA pairs
                qa_pairs_out: Dict = self.question_answer_generation_module.execute(
                    output_directory=directory,
                    initial_status=initial_status_qa_gen
                )
                self.on_qa_pairs_generated(qa_pairs_out)
                qa_pair_candidates: List[Dict] = qa_pairs_out[QuestionGenerator.VAL_PAIRS]

                for qa_pair in qa_pair_candidates:

                    if self.question_refine_module is not None:
                        qa_pair_out: Dict = self.question_refine_module.execute(
                            output_directory=directory,
                            initial_status=initial_status_qa_gen | {QuestionGenerator.VAL_CURRENT_PAIR: qa_pair}
                        )
                        qa_pair = qa_pair_out[QuestionGenerator.VAL_CURRENT_PAIR]

                    qa_candidate_value: Dict = selection_values | {
                        QuestionGenerator.VAL_CURRENT_PAIR: qa_pair
                    }
                    validation_results: List[Dict] = [
                        module.execute(
                            output_directory=directory,
                            initial_status=deepcopy(qa_candidate_value)
                        ) for module in self.validate_modules
                    ]

                    errors: List[Dict] = [r for r in validation_results if not r['is_valid']]
                    qa_pair_is_valid: bool = len(errors) == 0

                    qa_pair: QAPair = self._to_qa_pair(qa_candidate_value, validation_results, qa_pair_is_valid, values=qa_pairs_out, storyline=storyline)
                    self.generated_qa_pairs.append(qa_pair)

                    # Generate new questions for each QA pair
                    values: Dict = deepcopy(initial_status_qa_gen | {QuestionGenerator.VAL_CURRENT_PAIR: qa_pair})
                    for reviser in self.question_revisers:

                        revised_qa_pair_out: Dict = reviser.run(
                            directory=directory,
                            values=deepcopy(values)
                        )
                        qa_pairs = reviser.get_qa_pairs(revised_qa_pair_out, storyline, qa_pair)
                        self.generated_qa_pairs.extend(qa_pairs)
        except XMlParseError as err:
            print("Could not parse!")

