import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Cấu hình API Groq
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

# Hàm chia nhỏ văn bản để phù hợp với context size
def split_text(text, max_length=4000):
    sentences = text.split(". ")  # Chia theo câu
    chunks, chunk = [], ""
    for sentence in sentences:
        if len(chunk) + len(sentence) < max_length:
            chunk += sentence + ". "
        else:
            chunks.append(chunk.strip())
            chunk = sentence + ". "
    if chunk:
        chunks.append(chunk.strip())
    return chunks

# Hàm dịch nội dung
def translate_text(text, source_lang="Anh", target_lang="Việt", tone="Trang trọng, tự nhiên"):
    prompt = (f"Bạn là một chuyên gia dịch thuật. Hãy dịch đoạn văn sau từ {source_lang} sang {target_lang}.\n"
              f"Giữ nguyên ý nghĩa, giọng văn {tone}.\n"
              f"Nội dung: \n{text}")
    
    completion = client.chat.completions.create(
        messages=[{"role": "system", "content": "Bạn là chuyên gia dịch thuật chuyên nghiệp."},
                  {"role": "user", "content": prompt}],
        model="deepseek-r1-distill-llama-70b"
    )
    return completion.choices[0].message.content

# Hàm dịch file
def translate_file(input_file, output_file, source_lang="Anh", target_lang="Việt", tone="Trang trọng, tự nhiên"):
    with open(input_file, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    
    chunks = split_text(text)
    translated_chunks = [translate_text(chunk, source_lang, target_lang, tone) for chunk in chunks]
    
    translated_text = "\n".join(translated_chunks)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(translated_text)
    
    print(f"✅ Dịch xong! Kết quả lưu tại: {output_file}")

# Chạy chương trình
if __name__ == "__main__":
    input_file = input("📂 Nhập đường dẫn file cần dịch: ").strip()
    output_file = input("💾 Nhập đường dẫn file kết quả: ").strip()
    source_lang = input("🌍 Ngôn ngữ gốc: ").strip()
    target_lang = input("🎯 Ngôn ngữ đích: ").strip()
    tone = input("🎭 Giọng văn (VD: Trang trọng, Thân thiện, Học thuật...): ").strip()
    
    translate_file(input_file, output_file, source_lang, target_lang, tone)