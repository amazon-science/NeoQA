import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

from data_gen.llm.cache.llm_hash_cache import LLMCachePool, LLMHashCache
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.llm.wrapper.models.claude.claude_helper import ClaudeHelper
from data_gen.util.misc import hash_messages


def format_prompt_for_claude(prompt: str, how: str):
    if how not in {'chat'}:
        raise NotImplementedError(how)

    return f"User: {prompt}\nBot:"


CLAUDE_TO_REGION = {
    '3.0': 'us-east-1',
    '3.5': 'us-west-2'
}


CLAUDE_TO_NAME = {
    '3.0': 'anthropic.claude-3-sonnet-20240229-v1:0',
    '3.5': 'anthropic.claude-3-5-sonnet-20240620-v1:0'
}


class ClaudeWrapper(BaseLLMWrapper):

    def __init__(self, model_version: str = "3.5", temperature: float = 0.0,
                 max_tokens: int = 512):
        super().__init__()
        os.environ["AWS_DEFAULT_REGION"] = CLAUDE_TO_REGION[model_version]

        self.model: str = CLAUDE_TO_NAME[model_version]
        self.temperature: float = temperature
        self.max_tokens: int = max_tokens
        self.client: ClaudeHelper = ClaudeHelper(model=self.model)
        self.cache: LLMHashCache = LLMCachePool.get(temperature, max_tokens)

    def query(self, system_prompt: str, user_prompt: str, format_prompt: str = "chat") -> Dict:
        self.count_queries += 1
        assert system_prompt is None or system_prompt == ''

        messages: List[Dict] = [{"role": "user", "content": user_prompt}]
        messages_hash: str = hash_messages(messages)

        if not self.cache.has_hash(messages_hash, self.model):
            response: str = self.client.invoke_model_with_messages(
                system_prompt=system_prompt or "", messages=messages,
                max_gen_len=self.max_tokens,
                temperature=self.temperature
            )
            self.cache.add_result(messages_hash, json.dumps(messages), response, self.model)

        response: str = self.cache.get_result(messages_hash, self.model)
        return {
            'model_dump': None,
            'response': response
        }

    def query_history(self, system_prompt: str, prompt: str, history: List[Tuple[str, str]]) -> Dict:
        self.count_queries += 1
        messages: List[Dict] = []
        for llm_input, llm_output in history:
            messages.append({"role": "user", "content": f'{llm_input}'}),
            messages.append({"role": "assistant", "content": f'{llm_output}'}),
        messages.append({"role": "user", "content": prompt})

        messages_hash: str = hash_messages(messages, system_prompt=system_prompt)
        if not self.cache.has_hash(messages_hash, self.model):
            response: str = self.client.invoke_model_with_messages(
                system_prompt=system_prompt or "",
                messages=messages,
                max_gen_len=self.max_tokens,
                temperature=self.temperature
            )
            self.cache.add_result(messages_hash, json.dumps(messages), response, self.model)

        response: str = self.cache.get_result(messages_hash, self.model)
        return {
            'model_dump': None,
            'response': response
        }

    def get_info(self) -> Dict:
        return {
            'type': 'claude',
            'model': self.model,
            'temperature': self.temperature,
            'max-tokens': self.max_tokens
        }
