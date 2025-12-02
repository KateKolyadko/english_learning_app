import requests
import json

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50QGV4YW1wbGUuY29tIiwiZXhwIjoxNzY0NjQ2MDE3fQ.vauywb2pW-nsDN2rcmDVb8ivK8_LklQ1GwlTKnwIfBs"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

response = requests.get(
    "http://localhost:8000/api/v1/analysis/progress",
    headers=headers
)
print(f"Тест 1 - Прогресс пользователя:")
print(f"Статус: {response.status_code}")
print(f"Ответ: {response.text[:200]}...\n")


data = {
    "text": "English is an important language for international communication.",
    "title": "Test Essay"
}

response = requests.post(
    "http://localhost:8000/api/v1/analysis/essay",
    json=data,
    headers=headers
)
print(f"Тест 2 - Анализ эссе:")
print(f"Статус: {response.status_code}")
print(f"Ответ: {response.text}")


response = requests.post(
    "http://localhost:8000/api/v1/analysis/essay",
    json=data
)
print(f"\nТест 3 - Без токена:")
print(f"Статус: {response.status_code}")