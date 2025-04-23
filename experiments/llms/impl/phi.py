from typing import Dict, Optional, List

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

from experiments.llms.llm import LLM


class Phi(LLM):

    def __init__(
            self, path_or_name: str, temperature: float = 0.0, max_new_tokens: int = 3000,
            do_sample=False, top_k=None, top_p=None,
            name: Optional[str] = None
    ):
        super().__init__(temperature, max_new_tokens)
        self.name: str = name or path_or_name
        self.do_sample = do_sample
        self.top_k = top_k
        self.top_p = top_p

        model = AutoModelForCausalLM.from_pretrained(
            path_or_name,
            device_map="auto",
            torch_dtype="auto",
            trust_remote_code=True,
            attn_implementation="flash_attention_2"
        )
        tokenizer = AutoTokenizer.from_pretrained(path_or_name, trust_remote_code=True)
        self.pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )

        self.generation_args = {
            "max_new_tokens": self.max_new_tokens,
            "return_full_text": False,
            "temperature": self.temperature,
            "do_sample": self.do_sample,
            "top_k": self.top_k,
            'top_p': self.top_p
        }

    def get_name(self) -> str:
        return self.name

    def generate(self, instance: Dict) -> str:

        messages: List[Dict] = [
            {"role": "user", "content": instance['prompt']},
        ]

        output = self.pipe(messages, **self.generation_args)[0]['generated_text']
        return output
