import os
from openai import OpenAI

client=OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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",
)

# Khởi tạo lịch sử hội thoại
messages=[
    {
        "role": "system",
        "content": [
            "You are a helpful Vietnamese assistant.",
            "Always translate every message to Vietnamese.",
            "Each message is accompanied by specific references to reputable websites.",
        ],
    }
]

def chat_with_ai(user_input):
    # Thêm tin nhắn của người dùng vào lịch sử
    messages.append({"role": "user", "content": user_input})

    # Gửi lịch sử hội thoại lên API
    stream_chat_completion=client.chat.completions.create(
        messages=messages,
        model="deepseek-r1-distill-llama-70b",
        stream=True
    )

    # Nhận phản hồi từ bot
    response_content=""
    for chunk in stream_chat_completion:
        if chunk.choices[0].delta.content:
            response_content+=chunk.choices[0].delta.content
            print(chunk.choices[0].delta.content, end="", flush=True)

    print()

    # Thêm phản hồi của bot vào lịch sử
    messages.append({"role": "assistant", "content": response_content})

while True:
    user_input=input("Bạn: ")
    if user_input.lower() in ["exit", "quit", "thoát"]:
        break
    chat_with_ai(user_input)