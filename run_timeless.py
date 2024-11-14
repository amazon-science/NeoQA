"""
News Forest: A script to manage news-related tasks.

Usage:
  run_timeless.py all <model> <dataset-directory>
  run_timeless.py single <model> <dataset>


"""
import json
import os
from collections import defaultdict
from os import listdir, makedirs
from os.path import join, basename
from typing import List, Dict

from datasets import Dataset, tqdm
from docopt import docopt

from mglockne_story_line.inference.parse.mcq_json_extraction import MultipleChoiceAnswerSelectorJSON
from mglockne_story_line.util.file_util import read_jsonl, store_json
from src.mglockne_story_line.inference.prompts.get_multiple_choice_prompt import get_multiple_choice_prompt
from src.mglockne_story_line.llm.get_llm import get_llm
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.util.file_util import store_jsonl


def run_multiple_choice_inference_with_instances(model: BaseLLMWrapper, instances: List[Dict], evidence_type: str,  prompt_version: str = 'default-3') -> List[Dict]:
    out = []
    for entry in tqdm(instances):
        prompt: str = get_multiple_choice_prompt(prompt_version, entry, evidence_type=evidence_type)
        response: Dict = model.query('', prompt)
        # Undo stupid date parsing by datasets
        entry['date'] = entry['date'] # .strftime("%Y-%m-%d")
        for article in entry['evidence']:
            article['date'] = article['date'] # .strftime("%Y-%m-%d")
        out.append({
            'entry': entry,
            'prompt': prompt,
        } | response)
    return out



def run(model: str, dataset_path: str, out_dir: str, out_name: str):
    llm: BaseLLMWrapper = get_llm(model)
    instances: List[Dict] = read_jsonl(dataset_path)
    parser: MultipleChoiceAnswerSelectorJSON = MultipleChoiceAnswerSelectorJSON(7)

    # dataset: Dataset = get_dataset_timeless(dataset_path)
    predictions = run_multiple_choice_inference_with_instances(llm, instances, 'articles')
    for pred in predictions:
        pred['parsed'] = parser.select_answer(pred['response'], pred['entry']['answer_options'])
    makedirs(out_dir, exist_ok=True)
    out_path_pred: str = join(out_dir, basename(dataset_path).replace('.jsonl', '.predicted.jsonl'))
    store_jsonl(predictions, out_path_pred)


    count_correct = defaultdict(int)
    count_total = defaultdict(int)
    count_non_parsable = defaultdict(int)
    count_predicted_unknown = defaultdict(int)
    for pred in predictions:
        assert pred['entry']['answer_options'][pred['entry']['gold_answer_idx']] == pred['entry']['answer']
        question_type = pred['entry']['category']
        count_total[question_type] += 1
        is_correct: bool = pred['parsed']['answered'] == pred['entry']['gold_answer_idx']
        if pred['parsed']['answered'] >= 0:
            count_non_parsable[question_type] += 1
        if is_correct:
            count_correct[question_type] += 1
        if pred['entry']['answer_options'][pred['parsed']['answered']] == 'Unknown':
            count_predicted_unknown [question_type] += 1

        if 'insufficient' in dataset_path:
            assert pred['entry']['answer'] == 'Unknown'

    metrics = dict()
    for k in count_total:
        metrics[k] = {
            'count': count_total[k],
            'accuracy': count_correct[k]/count_total[k],
            'num_correct': count_correct[k],
            'num_unknown': count_predicted_unknown[k],
            'parsed': count_non_parsable[k]
        }
    metrics['total'] = {
        'count': sum(count_total.values()),
        'accuracy': sum(count_correct.values()) / sum(count_total.values()),
        'num_correct':  sum(count_correct.values()),
        'num_unknown': sum(count_predicted_unknown.values()),
        'parsed': sum(count_non_parsable.values())
    }

    out_path_metrics = out_path_pred.replace('.predicted.jsonl', '.metrics.json')
    print(json.dumps(metrics, indent=2))
    store_json(metrics, out_path_metrics, pretty=True)

def run_all(model, dataset_dir: str):

    for file in listdir(f'generated-datasets/{dataset_dir}'):
        pred_dir = f'predictions/{dataset_dir}/{model}'
        try:
            print(file)
            run(model, join(f'generated-datasets/{dataset_dir}', file), pred_dir, file)
        except Exception as err:
            print(err)
            raise err

# def run_single(model, dataset_file):
#     date = '2024-10-08/'
#     pred_dir = f'predictions/{date}/{model}'
#     run(model, join(f'generated-datasets/{date}', dataset_file), pred_dir, dataset_file)


def main():
    """
    Main function to parse command-line arguments using docopt and execute commands.
    """
    args = docopt(__doc__, version="Storyline 1.0")
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_PROFILE"] = "llmexp"

    model = args['<model>']
    dataset_dir: str = args['<dataset-directory>']

    if args['all']:
        run_all(model, dataset_dir)
    # elif args['single']:
    #     run_single(model, args['<dataset>'])




if __name__ == "__main__":
    main()