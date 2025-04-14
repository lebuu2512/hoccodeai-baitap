# Viết code để insert dữ liệu vào Weavite
import weaviate
import pandas as pd
import os
import kaggle
from weaviate.embedded import EmbeddedOptions
from weaviate.classes.config import Configure, Property, DataType, Tokenization

# Cấu hình embedded options
embedded_options = EmbeddedOptions(
    additional_env_vars={
        "ENABLE_MODULES": "backup-filesystem,text2vec-transformers",
        "BACKUP_FILESYSTEM_PATH": "/tmp/backups",
        "LOG_LEVEL": "panic",
        "TRANSFORMERS_INFERENCE_API": "http://localhost:8000"
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
    processed_data = []
    for row in data:
        processed_row = row.copy()
        
        # Xử lý is_prose: Chuyển float64 thành boolean
        if pd.notna(row.get('is_prose')):
            processed_row['is_prose'] = bool(row['is_prose'])
        else:
            processed_row['is_prose'] = False  # Giá trị mặc định nếu thiếu

        # Xử lý date: Chuyển chuỗi thành integer, bỏ qua NaN
        if pd.notna(row.get('date')):
            try:
                processed_row['date'] = int(float(row['date']))  # Đảm bảo integer
            except (ValueError, TypeError):
                processed_row['date'] = None  # Gán None nếu không hợp lệ
        else:
            processed_row['date'] = None

        # Xử lý lexile: Chuyển float thành string
        if pd.notna(row.get('lexile')):
            processed_row['lexile'] = str(row['lexile'])
        else:
            processed_row['lexile'] = ""

        # Xử lý genre: Chuyển string thành list (text array)
        if pd.notna(row.get('genre')):
            # Nếu genre là chuỗi, chuyển thành danh sách
            processed_row['genre'] = [str(row['genre'])] if isinstance(row['genre'], str) else row['genre']
        else:
            processed_row['genre'] = []

        processed_data.append(processed_row)
    return processed_data

def create_collection():
    try:
        # Tạo collection
        book_collection = vector_db_client.collections.create(
            name=COLLECTION_NAME,
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
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
        
        # Tải dataset từ Kaggle
        os.environ['KAGGLE_CONFIG_DIR'] = '~/.kaggle'
        dataset = 'kononenko/commonlit-texts'
        kaggle.api.dataset_download_files(dataset, path='.', unzip=True)

        # Đọc file CSV
        data = pd.read_csv('commonlit_texts.csv')
        
        # Tiền xử lý dữ liệu
        sent_to_vector_db = preprocess_data(data.to_dict(orient='records'))
        total_records = len(sent_to_vector_db)
        print(f"Inserting data to Vector DB. Total records: {total_records}")
        
        # Import dữ liệu vào DB theo batch
        with book_collection.batch.dynamic() as batch:
            for data_row in sent_to_vector_db:
                print(f"Inserting: {data_row['title']}")
                batch.add_object(properties=data_row)
        
        print("Data saved to Vector DB")
    finally:
        vector_db_client.close()
    
    
create_collection()    