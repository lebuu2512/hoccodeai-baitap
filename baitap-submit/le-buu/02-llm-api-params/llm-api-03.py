import requests
from bs4 import BeautifulSoup   
from openai import OpenAI

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key="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",
)

def get_vnexpress_article(url):
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to retrieve the page")
        return None
    
    soup = BeautifulSoup(response.text, "html.parser")
    main_detail = soup.find("div", id="main-detail")
    
    if not main_detail:
        print("No main-detail div found")
        return None
    
    title = main_detail.find("h1").text if main_detail.find("h1") else "No title found"
    description = main_detail.find("p", class_="description").text if main_detail.find("p", class_="description") else "No description found"
    content = "\n".join([p.text for p in main_detail.find_all("p", class_=lambda x: x != "description")])
    
    return {
        "title": title,
        "description": description,
        "content": content
    }

url = "https://tuoitre.vn/tong-bi-thu-to-lam-va-chu-tich-dang-cpp-hun-sen-chu-tri-cuoc-gap-cap-cao-tai-tp-hcm-20250221193615239.htm"  
article = get_vnexpress_article(url)
if article:
    print("Title:", article["title"])
    print("Description:", article["description"])
    print("Content:", article["content"])