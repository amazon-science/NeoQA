from typing import Dict, List

import spacy


class LexicalSimilarityFinder:
    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def normalize(self, text):
        tokens = [
            token.text.lower() for token in self.nlp(text) if not token.is_punct
        ]
        return tokens

    def rank_based_on_answer_overlap(self, answer: str, sentences: List[Dict]):
        normalized_answer = self.normalize(answer)

        scores_sentences = []
        for sent in sentences:
            normalized_sentence = self.normalize(sent['text'])
            answer_overlap = len(set(normalized_answer) & set(normalized_sentence))
            scores_sentences.append((sent, answer_overlap, len(normalized_sentence)))

        scores_sentences = sorted(scores_sentences, key=lambda x: (-x[-2], x[-1]))
        return [sent['id'] for sent, _, _ in scores_sentences]
