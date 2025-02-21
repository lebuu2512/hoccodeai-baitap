import requests
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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",
)

#Lấy nội dung bài báo bằng Jina Reader
def fetch_article_jina(url, max_length=5000):    
    api_url = f"https://r.jina.ai/{url}"
    response = requests.get(api_url)

    if response.status_code == 200:
        text = response.text.strip()
        return text[:max_length]  # Giới hạn độ dài
    else:
        print("❌ Không thể lấy nội dung bài báo!")
        return None

#Gửi nội dung lên AI để tóm tắt
def summarize_text(text):
    prompt = f"Tóm tắt bài báo sau bằng tiếng Việt:\n\n{text}"

    completion = client.chat.completions.create(
        messages=[{"role": "system", "content": "Bạn là trợ lý AI tóm tắt báo tiếng Việt."},
                  {"role": "user", "content": prompt}],
        model="deepseek-r1-distill-llama-70b"
    )

    return completion.choices[0].message.content

#Mở chatbot để tiếp tục trò chuyện về bài báo
def chat_about_article(summary):    
    print("\n🤖 Bắt đầu trò chuyện về bài báo. Nhập 'exit' để thoát.\n")

    messages = [
        {"role": "system", "content": "Bạn là trợ lý AI chuyên phân tích tin tức."},
        {"role": "user", "content": f"Tóm tắt bài báo:\n\n{summary}"}
    ]

    while True:
        user_input = input("🗨️ Bạn: ").strip()
        if user_input.lower() in ["exit", "quit", "thoát"]:
            print("👋 Kết thúc trò chuyện!")
            break

        messages.append({"role": "user", "content": user_input})

        completion = client.chat.completions.create(
            messages=messages,
            model="deepseek-r1-distill-llama-70b"
        )

        response = completion.choices[0].message.content
        print(f"🤖 AI: {response}")

        messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    url = input("🔗 Nhập link bài báo: ").strip()
    article_text = fetch_article_jina(url)

    if article_text:
        print("\n📌 --- Tóm tắt bài báo ---")
        summary = summarize_text(article_text)
        print(summary)

        # Bắt đầu chatbot
        chat_about_article(summary)
