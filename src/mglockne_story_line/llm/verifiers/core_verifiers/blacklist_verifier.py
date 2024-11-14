from typing import Set, List, Dict

import spacy

from src.mglockne_story_line.llm.verifiers.base_verifier import BaseVerifier, VerifyResult


class BlacklistVerifier(BaseVerifier):

    def __init__(self):
        super().__init__("BlacklistVerifier")
        self.nlp = spacy.load("en_core_web_md")
        self.blacklist_tokens = {
            'fictional', 'galactic'
        }


    def can_check(self) -> Set[str]:
        return {BaseVerifier.CAN_CHECK_TEXT}

    def check_text(self, text: str) -> VerifyResult:
        doc = self.nlp(text)
        errs: List[Dict] = []
        success: List[Dict] = []

        for sent in doc.sents:
            sent_blacklist_words: Set = set()
            for token in sent:
                if token.text.lower() in self.blacklist_tokens:
                    sent_blacklist_words.add(token.text.lower())
            if len(sent_blacklist_words) > 0:
                errs.append({
                    'sentence': sent.text, 'issues': list(sent_blacklist_words)
                })
            else:
                success.append({'sentence': sent.text})

        return VerifyResult(num_checked=len(list(doc.sents)), num_correct=len(success), errors=errs, success=success)



