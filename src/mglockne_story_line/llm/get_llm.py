from src.mglockne_story_line.llm.wrapper.models.claude_wrapper import ClaudeWrapper
from src.mglockne_story_line.llm.wrapper.models.gpt_wrapper import GPTWrapepr
from src.mglockne_story_line.llm.wrapper.models.llama3 import Llama3Wrapper


def get_llm(model_name, temperature: float = 0.0, max_tokens: int=512):
    if model_name == 'claude-35':
        return ClaudeWrapper(model_version='3.5', temperature=temperature, max_tokens=max_tokens)
    elif model_name == 'llama31-8b':
        return Llama3Wrapper('meta.llama3-1-8b-instruct-v1:0', temperature,  max_tokens)
    elif model_name == 'llama31-70b':
        return Llama3Wrapper('meta.llama3-1-70b-instruct-v1:0', temperature, max_tokens)
    elif model_name == 'gpt4-turbo':
        max_tokens = min((max_tokens, 4096))
        return GPTWrapepr('gpt-4-turbo-2024-04-09', temperature=temperature, max_tokens=max_tokens)
    else:
        raise NotImplementedError