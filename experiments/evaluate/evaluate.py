import json
from collections import defaultdict
from typing import Dict, List

import numpy as np
from sklearn.metrics import recall_score, precision_score, f1_score

from experiments.util.file_util import read_jsonl


def evaluate_predictions(predictions: List[Dict], add_answerable_scores: bool = False) -> Dict:

    num_parsed: int = 0
    num_correct: int = 0

    performance_per_answerable: Dict[bool, List[float]] = defaultdict(list)

    for prediction in predictions:
        predicted_answer_idx: int = prediction['predicted_answer']
        gold_answer_idx: int = prediction['gold_answer_idx']

        if predicted_answer_idx >= 0:
            num_parsed += 1

        if prediction['answerable'] in {'answerable-insufficient', 'unanswerable'}:
            answerable = False
        else:
            assert prediction['answerable'] == 'answerable-sufficient', prediction['answerable']
            answerable = True

        if predicted_answer_idx == gold_answer_idx:
            num_correct += 1
            performance_per_answerable[answerable].append(1.)
        else:
            performance_per_answerable[answerable].append(0.)

    out = {
        'total': len(predictions),
        'parsed': num_parsed / len(predictions),
        'accuracy': num_correct / len(predictions),
    }

    if add_answerable_scores:

        acc_answerable: float = float(np.mean(performance_per_answerable[True]))
        acc_unanswerable: float = float(np.mean(performance_per_answerable[False]))

        if acc_answerable + acc_unanswerable == 0.:
            overall_score: float = 0.
        else:
            overall_score: float = (2 * acc_answerable * acc_unanswerable) / (acc_answerable + acc_unanswerable)

        out['answerability_scores'] = {
            'answerable': acc_answerable,
            'unanswerable': acc_unanswerable,
            'overall': overall_score
        }
    return out


def adt_score(predictions: List[Dict]):
    correct_unanswerable: List[float] = []
    correct_answerable: List[float] = []
    for prediction in predictions:
        is_answerable: bool = prediction['answerable'] == 'answerable-sufficient'
        predicted_answer_idx: int = prediction['predicted_answer']
        gold_answer_idx: int = prediction['gold_answer_idx']

        if is_answerable:
            if predicted_answer_idx == gold_answer_idx:
                correct_answerable.append(1.)
            else:
                correct_answerable.append(0.)
        else:
            if predicted_answer_idx == gold_answer_idx:
                correct_unanswerable.append(1.)
            else:
                correct_unanswerable.append(0.)

    assert len(correct_unanswerable) > 0
    assert len(correct_answerable) > 0
    assert len(correct_unanswerable + correct_answerable) == len(predictions)

    acc_answerable = np.mean(correct_answerable)
    acc_unanswerable = np.mean(correct_unanswerable)
    if acc_answerable + acc_unanswerable == 0.:
        return {
            'adt': 0.,
            'acc_answerable': acc_answerable,
            'acc_unanswerable': acc_unanswerable
        }
    else:
        adt = (2 * acc_answerable * acc_unanswerable) / (acc_answerable + acc_unanswerable)
        return {
            'adt': adt,
            'acc_answerable': acc_answerable,
            'acc_unanswerable': acc_unanswerable
        }


def evaluate_file(src: str):
    predictions = read_jsonl(src)

    out: Dict = {
        'adt_score': adt_score(predictions),
        'acc_all': evaluate_predictions(predictions, True),
        'acc_sufficient_evidence': {
            'multi-hop': evaluate_predictions([
                p for p in predictions if p['answerable'] == 'answerable-sufficient' and p['category'] == 'multi-hop'
            ]),
            'time-span': evaluate_predictions([
                p for p in predictions if p['answerable'] == 'answerable-sufficient' and p['category'] == 'time-span'
            ]),
            'all': evaluate_predictions([
                p for p in predictions if p['answerable'] == 'answerable-sufficient'
            ]),
        },
        'acc_insufficient_evidence': {
            'multi-hop': evaluate_predictions([
                p for p in predictions if p['answerable'] == 'answerable-insufficient' and p['category'] == 'multi-hop'
            ]),
            'time-span': evaluate_predictions([
                p for p in predictions if p['answerable'] == 'answerable-insufficient' and p['category'] == 'time-span'
            ]),
            'all': evaluate_predictions([
                p for p in predictions if p['answerable'] == 'answerable-insufficient'
            ]),
        },
        'acc_unanswerable': {
            'uncertain-specificity': evaluate_predictions([
                p for p in predictions if p['category'] == 'uncertain-specificity'
            ]),
            'false-premise': evaluate_predictions([
                p for p in predictions if p['category'] == 'false-premise'
            ]),
            'all': evaluate_predictions([
                p for p in predictions if p['answerable'] == 'unanswerable'
            ]),
        }

    }

    print(json.dumps(out, indent=2))
    return out

