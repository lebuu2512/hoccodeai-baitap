import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="xxx",
)

stream_chat_completion=client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": [
                "You are a helpful vietnamese assistant.",
                "Always translate every messages to Vietnamese.",
                "Each message is accompanied by specific references to reputable websites.",
                ],
        },
        {
            "role": "user",
            "content": "List five important tasks to do to gain knowledge about A.I."
        },
    ],
    model="deepseek-r1-distill-llama-70b",
    stream=True
)
for chunk in stream_chat_completion:
    print(chunk.choices[0].delta.content or "", end="")