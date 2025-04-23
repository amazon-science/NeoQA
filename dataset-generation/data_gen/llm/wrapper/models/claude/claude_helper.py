import json
from typing import List, Dict

from data_gen.llm.wrapper.models.claude.bedrock_helper import BedrockHelper


class ClaudeHelper(BedrockHelper):
    def __init__(self, model):
        BedrockHelper.__init__(self, model)

    def invoke_model(self, system_prompt, user_prompt, max_gen_len=512, temperature=0):
        accept = "application/json"
        contentType = "application/json"

        data = {
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": max_gen_len,
            "temperature": temperature,
            "anthropic_version": "bedrock-2023-05-31",
        }
        if system_prompt is None:
            del data["system"]

        body = json.dumps(data)
        try:
            response = self.bedrock_runtime.invoke_model(
                body=body, modelId=self.model, accept=accept, contentType=contentType
            )
        except Exception as err:
            print('Got err:', err)
            BedrockHelper.__init__(self, self.model)
            response = self.bedrock_runtime.invoke_model(
                body=body, modelId=self.model, accept=accept, contentType=contentType
            )

        response_body = json.loads(response.get("body").read())
        return response_body["content"][0]["text"]

    def invoke_model_with_messages(self, system_prompt, messages: List[Dict], max_gen_len=512, temperature=0):
        accept = "application/json"
        contentType = "application/json"

        new_messages = []
        for msg in messages:
            content = msg['content']
            if msg['role'] == 'user':
                new_messages.append({"role": "user", "content": f'{content}'})
            else:
                new_messages.append({"role": "assistant", "content": f'{content}'})

        data = {
            "system": system_prompt,
            "messages": new_messages,
            "max_tokens": max_gen_len,
            "temperature": temperature,
            "anthropic_version": "bedrock-2023-05-31",
        }
        if system_prompt is None:
            del data["system"]

        body = json.dumps(data)
        try:
            response = self.bedrock_runtime.invoke_model(
                body=body, modelId=self.model, accept=accept, contentType=contentType
            )
        except Exception as err:
            BedrockHelper.__init__(self, self.model)
            response = self.bedrock_runtime.invoke_model(
                body=body, modelId=self.model, accept=accept, contentType=contentType
            )

        response_body = json.loads(response.get("body").read())
        return response_body["content"][0]["text"]