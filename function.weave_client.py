"""
title: Weave (Wandb) Context and Completion Logging
description: Weave (by Weights and Biases) context and completion logging for OpenWebUI
author: m-rgba (@martinmark)
author_url: https://github.com/m-rgba/openwebui-weave
version: 0.1
requirements: wandb, weave
"""

# Note: This is an alternate implementation that uses the Weave client SDK directly.
# For most use cases, you'll want to use function.py instead,
# which has no external dependencies and implements the same functionality using the Weave service API.

try:
    import wandb
except ImportError:
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "wandb"])
    import wandb

try:
    import weave
except ImportError:
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "weave"])
    import weave


import tiktoken
from pydantic import BaseModel, Field
from typing import List, Optional


class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=0, description="Priority level for the filter operations."
        )
        wandb_project_name: Optional[str] = Field(
            default=None,
            description="Weights & Biases project name for initialization in the format of `username/project_name`.",
        )
        wandb_api_key: Optional[str] = Field(
            default=None, description="Weights & Biases API key for login."
        )
        pass

    def __init__(self):
        self.valves = self.Valves()
        pass

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        wandb.login(key=self.valves.wandb_api_key)
        self.weave_client = weave.init(self.valves.wandb_project_name)
        # print(f"inlet:{__name__}")
        # print(f"inlet:body:{body}")
        # print(f"inlet:user:{__user__}")
        self.weave_call = self.weave_client.create_call(
            op=__name__,
            inputs={
                "messages": body.get("messages", []),
                "model": body.get("model", ""),
                "metadata": body.get("metadata", {}),
                "user": __user__,
            },
        )
        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # print(f"outlet:{__name__}")
        # print(f"outlet:body:{body}")
        # print(f"outlet:user:{__user__}")

        # Extract the last assistant message and its metadata
        messages = body.get("messages", [])
        last_assistant_message_obj = next(
            (msg for msg in reversed(messages) if msg.get("role") == "assistant"),
            None,
        )
        last_assistant_message = (
            last_assistant_message_obj.get("content")
            if last_assistant_message_obj
            else None
        )

        # Check if usage data is available in the last assistant message
        usage_data = (
            last_assistant_message_obj.get("info", {}).get("usage")
            if last_assistant_message_obj
            else None
        )
        model = body.get("model", "gpt-4o")
        if usage_data:
            usage_source = "API"
            # Use the provided usage data
            input_tokens = usage_data.get("prompt_tokens", 0)
            output_tokens = usage_data.get("completion_tokens", 0)
        else:
            usage_source = "Calculated"
            # Initialize tiktoken encoder and token buffers based on model
            # Approximate buffer from tiktoken as described here:
            # https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken#6-counting-tokens-for-chat-completions-api-calls
            try:
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                encoding = tiktoken.get_encoding("cl100k_base")
            # Calculate input tokens from all messages
            input_tokens = 0
            # print(messages)
            for message in messages:
                # Exclude last assistant response for input tokens
                if message is not last_assistant_message_obj:
                    message_content = message.get("content", "")
                    input_tokens += len(encoding.encode(str(message_content)))
                    input_tokens = input_tokens + 4

            # Calculate output tokens
            output_tokens = 0
            if last_assistant_message:
                output_tokens = len(encoding.encode(last_assistant_message))
                output_tokens = output_tokens + 3

        self.weave_client.finish_call(
            self.weave_call,
            output={
                "choices": [
                    {"message": {"content": last_assistant_message}},
                ],
                "model": model,
                "usage_source": usage_source,
                "usage": {
                    "completion_tokens": output_tokens,
                    "prompt_tokens": input_tokens,
                    "total_tokens": input_tokens + output_tokens,
                },
            },
        )
        return body
