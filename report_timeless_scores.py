"""
News Forest: A script to manage news-related tasks.

Usage:
  report_timeless_scores  <model>


"""
import json
import os
from collections import defaultdict, Counter
from os import listdir, makedirs
from os.path import join, basename
from typing import List, Dict

from datasets import Dataset, tqdm
from docopt import docopt

from mglockne_story_line.util.file_util import read_jsonl


def report_scores(model: str, directory: str='predictions/1410/subset-30'):
    # Make experiment dict
    prediction_dir = join(directory, model)
    prediction_dict = defaultdict(lambda: defaultdict(dict))
    for file in tqdm(listdir(prediction_dir)):
        if 'metrics' not in file and 'outlines' not in file:
            predictions = read_jsonl(join(prediction_dir, file))
            experiment = '-'.join(file.split('-')[1:]).replace('.jsonl', '')
            evidence_type = file.split('-')[0]
            for prediction in predictions:
                prediction['entry']['evidence'] = len(prediction['entry']['evidence'])
                prediction_dict[experiment][evidence_type][prediction['entry']['question_id']] = prediction

    experiments = sorted(list(prediction_dict.keys()))
    for experiment in experiments:
        print(experiment)
        answer_types = defaultdict(list)
        shared_keys = list(set(prediction_dict[experiment]['sufficient'].keys()) & set(prediction_dict[experiment]['insufficient'].keys()))
        for key in shared_keys:
            sufficient_question = prediction_dict[experiment]['sufficient'][key]
            insufficient_question = prediction_dict[experiment]['insufficient'][key]
            if sufficient_question['entry']['category'] in {'multi-hop', 'time-span'}:
                sufficient_answer: str = sufficient_question['entry']['answer']
                insufficient_answer: str = insufficient_question['entry']['answer']
                assert insufficient_answer == 'Unknown'
                if insufficient_question['parsed']['answered'] < 0:
                    insufficient_prediction_category = 'unk'
                else:
                    insufficient_predicted = insufficient_question['entry']['answer_options'][insufficient_question['parsed']['answered']]
                    assert sufficient_answer in insufficient_question['entry']['answer_options']
                    if insufficient_question['entry']['gold_answer_idx'] == insufficient_question['parsed']['answered']:
                        insufficient_prediction_category = 'correct-unknown'
                    elif insufficient_predicted == sufficient_answer:
                        insufficient_prediction_category = 'as-if-sufficient'
                    else:
                        insufficient_prediction_category = 'distractor'
                answer_types[sufficient_question['entry']['category']].append(insufficient_prediction_category)

        print('Insufficient types')

        for question_type in sorted(list(answer_types.keys())):
            print("QUESTION TYPE", question_type)
            for prediction_cat, count in Counter(answer_types[question_type]).most_common():
                print(prediction_cat, '-->', count, round(100*count/len(answer_types[question_type]), 1))
        print('---------\n\n')


def main():
    """
    Main function to parse command-line arguments using docopt and execute commands.
    """
    args = docopt(__doc__, version="Storyline 1.0")
    os.environ["AWS_DEFAULT_REGION"] = "us-west-2"
    os.environ["AWS_PROFILE"] = "llmexp"

    model = args['<model>']

    report_scores(model)
    # elif args['single']:
    #     run_single(model, args['<dataset>'])




if __name__ == "__main__":
    main()