# 1. Dùng chunking để làm bot trả lời tiểu sử người nổi tiếng, anime v...v
#   - <https://en.wikipedia.org/wiki/S%C6%A1n_T%C3%B9ng_M-TP>
#   - <https://en.wikipedia.org/wiki/Jujutsu_Kaisen>
import os
import spacy
from wikipediaapi import Wikipedia
from openai import OpenAI
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import inspect
from pydantic import BaseModel, TypeAdapter
import json
import gradio as gr

# Load mô hình ngôn ngữ tiếng Anh của spaCy
nlp = spacy.load("en_core_web_sm")

# Load biến môi trường
load_dotenv()
COLLECTION_NAME = "wiki_authors"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Khởi tạo Wikipedia API
wiki = Wikipedia('HocCodeAI/0.0 (https://hoccodeai.com)', 'en')

# Khởi tạo ChromaDB client và collection
client = chromadb.PersistentClient(path="./data_bio")
embedding_function = embedding_functions.DefaultEmbeddingFunction()
collection = client.get_or_create_collection(
    name=COLLECTION_NAME, embedding_function=embedding_function
)

# Khởi tạo OpenAI client (GROQ)
llm_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

def extract_person_names(question):
    """Trích xuất tên các nhân vật nổi tiếng từ câu hỏi bằng spacy"""
    doc = nlp(question)
    persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    return persons

class WikipediaQueryInput(BaseModel):
    query: str

def get_wikipedia_text(query: str) -> bool:
    """Lấy nội dung Wikipedia của các nhân vật từ câu hỏi và lưu trữ nếu chưa có."""
    persons = extract_person_names(query)

    if not persons:
        return False

    for person in persons:
        existing_docs = collection.peek()["metadatas"] if collection.peek() else []
        if any(doc["author"] == person for doc in existing_docs):
            print(f"Dữ liệu của {person} đã có trong ChromaDB, bỏ qua tải lại.")
            continue

        wiki_page = wiki.page(person.replace(" ", "_"))
        if wiki_page.exists():
            print(f"Đang tìm kiếm thông tin về {person} trên wikipedia")
            text = wiki_page.text
            store_in_chromadb(text, person)

    return True

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_wikipedia_text",
            "description": inspect.getdoc(get_wikipedia_text),
            "parameters": TypeAdapter(WikipediaQueryInput).json_schema()
        }
    }
]

def store_in_chromadb(text, author_name):
    """Lưu dữ liệu vào ChromaDB với metadata là tên nhân vật để không bị ghi đè."""
    paragraphs = text.split("\n\n")
    existing_docs = collection.peek()["ids"] if collection.peek() else []

    for index, paragraph in enumerate(paragraphs):
        doc_id = f"{author_name}_{index}"
        if doc_id not in existing_docs:
            print(f"Tên nhân vật {author_name} chưa có trong ChromaDB... đang thêm vào db")
            collection.add(documents=[paragraph], ids=[doc_id], metadatas=[{"author": author_name}])

    print(f"Dữ liệu của {author_name} đã được lưu vào ChromaDB.")

def retrieve_and_answer(query, history):
    """Truy vấn dữ liệu từ ChromaDB và trả lời dựa trên RAG."""
    persons = extract_person_names(query)
    
    # Luôn cố gắng lấy dữ liệu từ Wikipedia nếu chưa có
    get_wikipedia_text(query)

    # Truy vấn ChromaDB
    if persons:
        q = collection.query(
            query_texts=[query],
            n_results=5,
            where={"author": persons[0]}
        )
    else:
        q = collection.query(
            query_texts=[query],
            n_results=5
        )

    if not q["documents"]:
        return "Không tìm thấy thông tin phù hợp trong cơ sở dữ liệu."

    CONTEXT = q["documents"][0]

    messages = [{"role": "system", "content": "You are a helpful chatbot that always uses retrieved Wikipedia data to answer questions."}]
    for user_msg, bot_msg in history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": bot_msg})
    messages.append({"role": "user", "content": f"CONTEXT: {CONTEXT}\nQUESTION: {query}"})

    response = llm_client.chat.completions.create(
        model="gemma2-9b-it",
        messages=messages
    )

    return response.choices[0].message.content

def process_query(message, history):
    """Xử lý câu hỏi từ Gradio, luôn sử dụng RAG, và trả về lịch sử trò chuyện."""
    query = message

    # Luôn gọi RAG để trả lời
    answer = retrieve_and_answer(query, history)

    # Cập nhật lịch sử trò chuyện
    updated_history = history + [[message, answer]]
    return updated_history

# Tạo giao diện Gradio
with gr.Blocks(title="Chatbot Wikipedia") as demo:
    chatbot = gr.Chatbot(label="Chatbot")
    msg = gr.Textbox(label="Nhập câu hỏi của bạn", placeholder="Ví dụ: Tell me about Nguyen Nhat Anh")
    clear = gr.Button("Xóa lịch sử")

    # Liên kết hàm process_query với giao diện
    msg.submit(process_query, inputs=[msg, chatbot], outputs=chatbot)
    clear.click(lambda: [], None, chatbot)

# Chạy ứng dụng
demo.launch()