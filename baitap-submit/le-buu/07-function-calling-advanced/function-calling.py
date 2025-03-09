import os
import json
import inspect
import requests
from openai import  OpenAI
from pydantic import TypeAdapter
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

# Implement 3 hàm

def get_current_weather(location: str, unit: str):
    """Get the current weather in a given location"""
    # Hardcoded response for demo purposes
    return "Trời rét vãi nôi, 7 độ C"


def get_stock_price(symbol: str):
    # Không làm gì cả, để hàm trống
    pass


# Bài 2: Implement hàm `view_website`, sử dụng `requests` và JinaAI để đọc markdown từ URL
def view_website(url: str) -> str:
    """
    View a website and return its content in Markdown format using Jina AI.    
    Args:
        url (str): The URL of the website to view.    
    Returns:
        str: The website content in Markdown format.    
    Raises:
        requests.RequestException: If the request to Jina AI fails.
    """
    # URL của Jina Reader API
    jina_reader_url = "https://r.jina.ai/"
    
    try:
        # Gửi yêu cầu GET tới Jina Reader với URL mục tiêu
        response = requests.get(f"{jina_reader_url}{url}", timeout=10)
        
        # Kiểm tra xem yêu cầu có thành công không (status code 200)
        response.raise_for_status()
        
        # Trả về nội dung Markdown từ phản hồi
        return response.text
    
    except requests.RequestException as e:
        # Xử lý lỗi nếu yêu cầu thất bại
        return f"Error fetching website content: {str(e)}"


# Bài 1: Thay vì tự viết object `tools`, hãy xem lại bài trước, sửa code và dùng `inspect` và `TypeAdapter` để define `tools`
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": inspect.getdoc(get_current_weather),
            "parameters": TypeAdapter(get_current_weather).json_schema()
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "Get the current stock price of a given symbol",
            "parameters": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_website",
            "description": inspect.getdoc(view_website),
            "parameters": TypeAdapter(view_website).json_schema()
        }
    }
]

# https://platform.openai.com/api-keys
client = OpenAI(
    base_url= "https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)
COMPLETION_MODEL = "gemma2-9b-it"

messages = [{"role": "user", "content": "Xem nội dung trang web https://example.com"}]

print("Bước 1: Gửi message lên cho LLM")
pprint(messages)

response = client.chat.completions.create(
    model=COMPLETION_MODEL,
    messages=messages,
    tools=tools
)

print("Bước 2: LLM đọc và phân tích ngữ cảnh LLM")
pprint(response)

print("Bước 3: Lấy kết quả từ LLM")
tool_calls = response.choices[0].message.tool_calls
if tool_calls and len(tool_calls) > 0:
    tool_call = tool_calls[0]
    pprint(tool_call)
    arguments = json.loads(tool_call.function.arguments)

    print("Bước 4: Chạy function tương ứng ở máy mình")
    if tool_call.function.name == 'get_current_weather':
        weather_result = get_current_weather(arguments.get('location'), arguments.get('unit'))
        print(f"Kết quả bước 4: {weather_result}")
        tool_result = weather_result

    elif tool_call.function.name == 'view_website':
        website_content = view_website(arguments.get('url'))
        print(f"Kết quả bước 4: Nội dung trang web:\n{website_content}")
        tool_result = website_content

    else:
        print(f"Công cụ {tool_call.function.name} chưa được triển khai.")
        tool_result = "Chưa triển khai"

    print("Bước 5: Gửi kết quả lên cho LLM")
    messages.append(response.choices[0].message)
    messages.append({
        "role": "tool",
        "content": tool_result,
        "tool_call_id": tool_call.id
    })

    pprint(messages)

    final_response = client.chat.completions.create(
        model=COMPLETION_MODEL,
        messages=messages
    )
    if final_response.choices and final_response.choices[0].message.content:
        print(f"Kết quả cuối cùng từ LLM: {final_response.choices[0].message.content}.")
    else:
        print("Không nhận được phản hồi cuối cùng từ LLM.")
else:
    print("Không có tool call nào được trả về, nội dung trực tiếp:", response.choices[0].message.content)
