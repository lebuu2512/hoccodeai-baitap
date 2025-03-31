# 2. Thay vì hardcode `doc = wiki.page('Hayao_Miyazaki').text`, sử dụng function calling để:
#   - Lấy thông tin cần tìm từ câu hỏi
#   - Dùng `wiki.page` để lấy thông tin về
#   - Sử dụng RAG để có kết quả trả lời đúng.
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
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Load mô hình ngôn ngữ tiếng Anh của spaCy
nlp = spacy.load("en_core_web_sm")

# Load biến môi trường
load_dotenv()
COLLECTION_NAME = "wiki_authors"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Khởi tạo Wikipedia API
wiki = Wikipedia('HocCodeAI/0.0 (https://hoccodeai.com)', 'en')

# Khởi tạo ChromaDB client và collection
client = chromadb.PersistentClient(path="./data_ask")
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
    """Trích xuất tên các nhân vật nổi tiếng từ câu hỏi bằng spacy."""
    doc = nlp(question)
    persons = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    return persons

class WikipediaQueryInput(BaseModel):
    query: str

def get_wikipedia_text(query: str) -> bool:
    """
    Lấy nội dung Wikipedia của các nhân vật từ câu hỏi và lưu trữ nếu chưa có.
    
    Args:
        query (str): Câu hỏi chứa tên nhân vật.
    
    Returns:
        bool: Trả về `True` nếu có dữ liệu mới được lưu, ngược lại là `False`.
    """
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
            print(f"Lấy thông tin của {person} trên Wikipedia")
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

#Chunking
text_spliter = RecursiveCharacterTextSplitter(
    chunk_size = 400,
    chunk_overlap = 80
)
def store_in_chromadb(text, author_name):
    """Lưu dữ liệu vào ChromaDB với metadata là tên nhân vật để không bị ghi đè."""
    paragraphs = text_spliter.split_text(text)    
    existing_docs = collection.peek()["ids"] if collection.peek() else []

    for index, paragraph in enumerate(paragraphs):
        doc_id = f"{author_name}_{index}"
        if doc_id not in existing_docs:
            print(f"{paragraph} - id: {doc_id} ")
            collection.add(documents=[paragraph], ids=[doc_id], metadatas=[{"author": author_name}])

    print(f"Dữ liệu của {author_name} đã được lưu vào ChromaDB.")

def retrieve_and_answer(query):
    """Truy vấn dữ liệu chỉ liên quan đến nhân vật trong câu hỏi."""
    persons = extract_person_names(query)
    
    if not persons:
        return "Không tìm thấy nhân vật trong câu hỏi."

    q = collection.query(
        query_texts=[query],
        n_results=5,
        where={"author": persons[0]}
    )

    if not q["documents"]:
        return "Không tìm thấy thông tin phù hợp."

    CONTEXT = q["documents"][0]

    prompt = f"""
    Use the following CONTEXT to answer the QUESTION at the end.
    If you don't know the answer, just say that you don't know, don't try to make up an answer.
    Use an unbiased and journalistic tone.

    CONTEXT: {CONTEXT}

    QUESTION: {query}
    """

    response = llm_client.chat.completions.create(
        model="gemma2-9b-it",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content

def process_query(query):
    """Xử lý câu hỏi với function calling."""
    # Bước 1: Gọi API với tool calling
    response = llm_client.chat.completions.create(
        model="gemma2-9b-it",
        messages=[
            {"role": "system", "content": "You have access to Wikipedia retrieval tools."},
            {"role": "user", "content": query}
        ],
        tools=tools,
        tool_choice="auto"
    )

    # Bước 2: Kiểm tra xem API có yêu cầu gọi hàm không
    if response.choices[0].message.tool_calls:
        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name == "get_wikipedia_text":
            # Lấy tham số từ tool call
            args = json.loads(tool_call.function.arguments)
            # Thực thi hàm get_wikipedia_text
            get_wikipedia_text(args["query"])

    # Bước 3: Truy vấn và trả lời
    answer = retrieve_and_answer(query)
    return answer

# Thử nghiệm
query = "Tell me about Nikolai A.Ostrovsky"
answer = process_query(query)
print(answer)