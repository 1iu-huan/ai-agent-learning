import requests

response = requests.post(
    "http://localhost:8000/ask",
    json={"question": "迟到会扣钱吗？"}
)
print(response.json())