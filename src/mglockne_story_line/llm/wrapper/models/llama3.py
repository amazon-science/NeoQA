from typing import List, Tuple, Dict, Optional

from src.mglockne_story_line.llm.cache.llm_hash_cache import LLMHashCache, LLMCachePool
from src.mglockne_story_line.llm.wrapper.base_llm_wrapper import BaseLLMWrapper
from src.mglockne_story_line.llm.wrapper.models.llama.llama_bedrock_helper import Llama3BedrockHelper
from src.mglockne_story_line.util.misc import hash_query_string


def _build_query_llama3(system_prompt: str, prompt: str) -> str:
    query: str = f'<|begin_of_text|>'

    # This was (omitted)) 05. Sept (after the 70B runs)
    if len(system_prompt) > 0:
        query += f'<|start_header_id|>system<|end_header_id|>{system_prompt}<|eot_id|>'
    query += f'<|start_header_id|>user<|end_header_id|>{prompt}<|eot_id|>'
    query += '<|start_header_id|>assistant<|end_header_id|>'
    return query


def _build_query_llama2(system_prompt: str, prompt: str) -> str:
    query: str = f'<s>[INST]'
    if len(system_prompt) > 0:
        query += f'<<SYS>>\n{system_prompt}\n<</SYS>>'

    query += f'\n{prompt} [/INST]'
    return query


class Llama3Wrapper(BaseLLMWrapper):

    def __init__(self, llm_name: str, temperature: float, max_tokens: int, system_prompt: Optional[str] = None):
        super().__init__()
        self.llm_name: str = llm_name
        self.system_prompt: str = system_prompt or ''
        self.temperature: float = temperature
        self.max_tokens: int = max_tokens
        self.cache: LLMHashCache = LLMCachePool.get(temperature, max_tokens)
        self.bedrock: Llama3BedrockHelper = Llama3BedrockHelper(model=llm_name)

    def get_info(self) -> Dict:
        return {
            'name': self.llm_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }

    def prompt(self, prompt: str) -> Dict:
        return self.query(self.system_prompt, prompt)

    def query(self, system_prompt: str, prompt: str) -> Dict:
        self.count_queries += 1

        if 'llama3' in self.llm_name:
            query: str = _build_query_llama3(system_prompt, prompt)
        elif 'llama2' in self.llm_name:
            query = _build_query_llama2(system_prompt, prompt)
        else:
            raise ValueError(self.llm_name)
        query_hash: str = hash_query_string(query)
        if not self.cache.has_hash(query_hash, self.llm_name):
            response = self.bedrock.invoke_model(prompt=query, max_gen_len=self.max_tokens, temperature=self.temperature)
            self.cache.add_result(query_hash, query, response, self.llm_name)

        return {
            'model_dump': self.get_info(),
            'response': self.cache.get_result(query_hash, self.llm_name)
        }


    def query_history(self, system_prompt: str, prompt: str, history: List[Tuple[str, str]]) -> Dict:
        raise NotImplementedError()


