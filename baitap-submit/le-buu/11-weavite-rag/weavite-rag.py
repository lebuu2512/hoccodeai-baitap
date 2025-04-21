# Áp dụng Weaviate để tạo ra một RAG flow đơn giản, gợi ý sách hay, dựa theo query của người dùng.
# Thay vì hard code query, hãy lấy query từ người dùng input ở console, hoặc tạo app bằng Gradio.
import weaviate
from weaviate.embedded import EmbeddedOptions
from weaviate.classes.config import Configure, Property, DataType, Tokenization
import pandas as pd
import os
import kaggle
from dotenv import load_dotenv
import gradio as gr

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Cấu hình embedded options
embedded_options = EmbeddedOptions(
    additional_env_vars={
        "ENABLE_MODULES": "backup-filesystem,text2vec-transformers,generative-openai",
        "BACKUP_FILESYSTEM_PATH": "/tmp/backups",
        "LOG_LEVEL": "panic",
        "TRANSFORMERS_INFERENCE_API": "http://localhost:8000",
        "OPENAI_APIKEY": OPENAI_API_KEY
    },
    persistence_data_path="book_data",
)

# Kết nối tới Weaviate
vector_db_client = weaviate.WeaviateClient(embedded_options=embedded_options)
vector_db_client.connect()
print("DB is ready: {}".format(vector_db_client.is_ready()))

COLLECTION_NAME = "BookCollection"

def preprocess_data(data):
    """Tiền xử lý dữ liệu để đảm bảo khớp với schema của Weaviate."""
    df = pd.DataFrame(data)
    
    if 'is_prose' in df.columns:
        df['is_prose'] = df['is_prose'].fillna(False).astype(bool)
    
    if 'date' in df.columns:
        df['date'] = pd.to_numeric(df['date'], errors='coerce').fillna(pd.NA).astype('Int64')
    
    if 'lexile' in df.columns:
        df['lexile'] = df['lexile'].astype(str).replace('nan', '')
    
    if 'genre' in df.columns:
        df['genre'] = df.apply(
            lambda row: [str(row['genre'])] if pd.notna(row['genre']) and isinstance(row['genre'], str) 
            else (row['genre'] if isinstance(row['genre'], list) else []), 
            axis=1
        )
    
    processed_data = []
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        for key, value in row_dict.items():
            if pd.isna(value):
                if key == 'is_prose':
                    row_dict[key] = False
                elif key == 'date':
                    row_dict[key] = None
                elif key == 'lexile':
                    row_dict[key] = ""
                elif key == 'genre':
                    row_dict[key] = []
        processed_data.append(row_dict)
    
    return processed_data

def create_collection():
    book_collection = vector_db_client.collections.create(
        name=COLLECTION_NAME,
        vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
        generative_config=Configure.Generative.openai(
            model="gpt-4o-mini"
        ),
        properties=[
            Property(name="title", data_type=DataType.TEXT, vectorize_property_name=True, tokenization=Tokenization.LOWERCASE),
            Property(name="author", data_type=DataType.TEXT, vectorize_property_name=True, tokenization=Tokenization.WORD),
            Property(name="description", data_type=DataType.TEXT, vectorize_property_name=True, tokenization=Tokenization.WHITESPACE),
            Property(name="grade", data_type=DataType.INT, skip_vectorization=True),
            Property(name="genre", data_type=DataType.TEXT_ARRAY, vectorize_property_name=True, tokenization=Tokenization.WORD),
            Property(name="lexile", data_type=DataType.TEXT, skip_vectorization=True),
            Property(name="path", data_type=DataType.TEXT, skip_vectorization=True),
            Property(name="is_prose", data_type=DataType.BOOL, skip_vectorization=True),
            Property(name="date", data_type=DataType.INT, skip_vectorization=True),
            Property(name="intro", data_type=DataType.TEXT, vectorize_property_name=True, tokenization=Tokenization.WHITESPACE),
            Property(name="excerpt", data_type=DataType.TEXT, vectorize_property_name=True, tokenization=Tokenization.WHITESPACE),
            Property(name="license", data_type=DataType.TEXT, skip_vectorization=True),
            Property(name="notes", data_type=DataType.TEXT, vectorize_property_name=True, tokenization=Tokenization.WHITESPACE),
        ]
    )
    
    os.environ['KAGGLE_CONFIG_DIR'] = '~/.kaggle'
    dataset = 'kononenko/commonlit-texts'
    kaggle.api.dataset_download_files(dataset, path='.', unzip=True)

    data = pd.read_csv('commonlit_texts.csv')
    
    sent_to_vector_db = preprocess_data(data.to_dict(orient='records'))
    total_records = len(sent_to_vector_db)
    print(f"Inserting data to Vector DB. Total records: {total_records}")
    
    with book_collection.batch.dynamic() as batch:
        for data_row in sent_to_vector_db:
            print(f"Inserting: {data_row['title']}")
            batch.add_object(properties=data_row)
    
    print("Data saved to Vector DB")
    
def search_books(query, limit=3):
    try:
        vector_db_client.connect()
        book_collection = vector_db_client.collections.get(COLLECTION_NAME)
        
        response = book_collection.generate.near_text(
            query=query,
            grouped_task="Suggest good books from the data found and write a short introduction to these books.",
            limit=limit,
        )
            
        results = []
        for obj in response.objects:
            book_info = f"**Title**: {obj.properties['title']}\n" \
                        f"**Author**: {obj.properties.get('author', 'Unknown')}\n" \
                        f"**Description**: {obj.properties.get('description', 'No description available')}\n" \
                        f"**Genre**: {', '.join(obj.properties.get('genre', []))}\n"
            results.append(book_info)
        
        generated_text = response.generated if response.generated else "No generated text available."
        
        return "\n\n".join(results), generated_text
    
    except Exception as e:
        return f"Error: {str(e)}", ""
    
    finally:
        vector_db_client.close()

def gradio_search(query, limit=3):
    if not query:
        return "Please enter a search query.", ""
    books, generated = search_books(query, limit)
    return books, generated

# Tạo giao diện Gradio
with gr.Blocks() as demo:
    gr.Markdown("# Book Search Application")
    query_input = gr.Textbox(label="Enter the book genre (e.g., 'Funny')")
    limit_input = gr.Slider(minimum=1, maximum=10, value=3, step=1, label="Number of results")
    search_button = gr.Button("Search")
    books_output = gr.Markdown(label="Search Results")
    generated_output = gr.Markdown(label="Generated Recommendation")
    
    search_button.click(
        fn=gradio_search,
        inputs=[query_input, limit_input],
        outputs=[books_output, generated_output]
    )

# Kiểm tra và tạo collection nếu cần
if not vector_db_client.collections.exists(COLLECTION_NAME):
    create_collection()

# Khởi chạy ứng dụng Gradio
demo.launch()