"""
title: Weave (Wandb) Context and Completion Logging
description: Weave (by Weights and Biases) context and completion logging for OpenWebUI
author: m-rgba (@martinmark)
author_url: https://github.com/m-rgba/openwebui-weave
version: 0.1
"""

import datetime
import tiktoken
import requests
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
        # print(f"inlet:{__name__}")
        # print(f"inlet:body:{body}")
        # print(f"inlet:user:{__user__}")
        url = "https://trace.wandb.ai/call/start"
        headers = {"content-type": "application/json"}
        payload = {
            "start": {
                "project_id": self.valves.wandb_project_name,
                "op_name": __name__,
                "started_at": datetime.datetime.now().isoformat(),
                "inputs": {
                    "messages": body.get("messages", []),
                    "model": body.get("model", ""),
                    "metadata": body.get("metadata", {}),
                    "user": __user__,
                },
                "attributes": {},
            }
        }
        response = requests.post(
            url, headers=headers, json=payload, auth=("api", self.valves.wandb_api_key)
        )
        if response.status_code == 200:
            # print("Start request successful")
            data = response.json()
            self.trace_id = data.get("id")
        else:
            print("Start request failed with status:", response.status_code)
            print(response.text)
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

        # Build the payload
        payload = {
            "end": {
                "project_id": self.valves.wandb_project_name,
                "id": self.trace_id,
                "ended_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "output": {
                    "choices": [
                        {"message": {"content": last_assistant_message}},
                    ],
                    "usage_source": usage_source,
                },
                "summary": {
                    "usage": {
                        model: {
                            "prompt_tokens": input_tokens,
                            "completion_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens,
                            "requests": 1,
                        }
                    }
                },
            }
        }
        # Send end request
        url = "https://trace.wandb.ai/call/end"
        headers = {"content-type": "application/json"}
        response = requests.post(
            url, headers=headers, json=payload, auth=("api", self.valves.wandb_api_key)
        )
        if response.status_code == 200:
            # print("End request successful")
            data = response.json()
            # print(f"outlet:data:{data}")
        else:
            print("End request failed with status:", response.status_code)
            print(response.text)
        return body
