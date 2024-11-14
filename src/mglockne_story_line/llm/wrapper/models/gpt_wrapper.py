import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

import pandas as pd
from openai import OpenAI

from src.mglockne_story_line.llm.cache.llm_hash_cache import LLMHashCache, LLMCachePool
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.llm.wrapper.models.claude.claude_helper import ClaudeHelper
from src.mglockne_story_line.util.misc import hash_messages


class GPTWrapepr(BaseLLMWrapper):


    def __init__(self, model_version: str = "gpt-4-turbo-2024-04-09", temperature: float = 0.0,
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
            start_time = datetime.now()
            print(f'Prompt Start: {start_time}.')
            response: str = self.invoke_model_with_messages(
                system_prompt=system_prompt or "", messages=messages,
                max_gen_len=self.max_tokens,
                temperature=self.temperature
            )
            self.cache.add_result(messages_hash, json.dumps(messages), response, self.model)
            end_time = datetime.now()
            print(f'Prompt End: {end_time}. ({end_time - start_time})')

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
            start_time = datetime.now()
            print(f'Prompt Start: {start_time}. History: {len(history)}')
            print('Number of messages:', len(messages))
            response: str = self.invoke_model_with_messages(
                system_prompt=system_prompt or "",
                messages=messages,
                max_gen_len=self.max_tokens,
                temperature=self.temperature
            )
            end_time = datetime.now()
            print(f'Prompt End: {end_time}. ({end_time - start_time})')
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

        # TODO make robust!
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_gen_len
        )
        return response.choices[0].message.content

