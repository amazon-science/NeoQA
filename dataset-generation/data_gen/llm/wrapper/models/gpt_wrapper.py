import json
import time
from typing import Dict, List, Tuple

import openai
from openai import OpenAI

from data_gen.llm.cache.llm_hash_cache import LLMHashCache, LLMCachePool
from data_gen.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from data_gen.util.misc import hash_messages


class GPTWrapper(BaseLLMWrapper):

    def __init__(self, model_version: str = "gpt-4o-2024-11-20", temperature: float = 0.0,
                 max_tokens: int = 512):
        super().__init__()

        self.model: str = model_version
        self.temperature: float = temperature
        self.max_tokens: int = max_tokens
        self.cache: LLMHashCache = LLMCachePool.get(temperature, max_tokens)
        self.client = OpenAI()

    def query(self, system_prompt: str, user_prompt: str, format_prompt: str = "chat") -> Dict:
        self.count_queries += 1
        assert system_prompt is None or system_prompt == ''

        messages: List[Dict] = [{"role": "user", "content": user_prompt}]
        messages_hash: str = hash_messages(messages)

        if not self.cache.has_hash(messages_hash, self.model):
            response: str = self.invoke_model_with_messages(
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
            response: str = self.invoke_model_with_messages(
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
            'type': 'gpt',
            'model': self.model,
            'temperature': self.temperature,
            'max-tokens': self.max_tokens
        }

    def invoke_model_with_messages(self, system_prompt, messages: List[Dict], max_gen_len=512, temperature: float=0.):

        attempts: int = 0

        while attempts < 10:
            attempts += 1
            try:
                new_messages = []

                if system_prompt is not None and len(system_prompt.strip()) > 0:
                    new_messages.append({
                        'role': 'system', 'content': system_prompt
                    })

                for msg in messages:
                    content = msg['content']
                    if msg['role'] == 'user':
                        new_messages.append({"role": "user", "content": f'{content}'})
                    else:
                        new_messages.append({"role": "assistant", "content": f'{content}'})

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_gen_len
                )
                return response.choices[0].message.content
            except openai.RateLimitError as err:
                print('Ratelimit Error')
                print(err)
                print('Sleeping for 5 seconds.')
                time.sleep(5)
        raise ValueError('Ratelimit exceeded too many times!')

