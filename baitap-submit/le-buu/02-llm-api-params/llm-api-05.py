import os
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

#Gửi câu hỏi cho AI và nhận code trả về.
def generate_code(question, language="python"):
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.getenv("GROQ_API_KEY")
    )
    
    prompt = f"Viết code {language} để giải quyết yêu cầu sau:\n{question}"
    completion = client.chat.completions.create(
        messages=[{"role": "system", "content": "Bạn là trợ lý lập trình."},
                  {"role": "user", "content": prompt}],
        model="deepseek-r1-distill-llama-70b"
    )
    
    return completion.choices[0].message.content

#Lưu code vào file và chạy thử.
def save_and_run_code(code, filename="final.py"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code)
    
    print(f"✅ Code đã được lưu vào {filename}")
    print("▶️ Đang chạy thử...")
    os.system(f"python {filename}")

if __name__ == "__main__":
    question = input("📝 Nhập bài toán lập trình: ")
    language = "python"  # Mặc định dùng Python
    
    code = generate_code(question, language)
    print("\n📜 Code AI tạo ra:\n", code)
    
    save_and_run_code(code)