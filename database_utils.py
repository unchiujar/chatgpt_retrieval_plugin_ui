from typing import Any, Dict
import requests
import os
from secrets import DATABASE_INTERFACE_BEARER_TOKEN

SEARCH_TOP_K = 3


def upsert_file(directory: str):
  """
  Upload all files under a directory to the vector database.
  """
  url = "http://0.0.0.0:8000/upsert-file"
  headers = {"Authorization": "Bearer " + DATABASE_INTERFACE_BEARER_TOKEN}
  files = []
  for root, dirs, files in os.walk(directory,  followlinks=True):
    for filename in files:
      file_path = os.path.join(root, filename)
      relative_path = os.path.relpath(file_path, directory)
      with open(file_path, "rb") as f:
        file_content = f.read()
      # Create a new list for each file
      file_list = [("file", (relative_path, file_content, "text/plain"))]
      response = requests.post(url, headers=headers, files=file_list, timeout=600)
      if response.status_code == 200:
        print(relative_path + " uploaded successfully.")
      else:
        print(f"Error: {response.status_code} {response.content} for uploading " + relative_path)

def upsert(id: str, content: str):
  """
  Upload one piece of text to the database.
  """
  url = "http://0.0.0.0:8000/upsert"
  headers = {
    "accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Bearer " + DATABASE_INTERFACE_BEARER_TOKEN,
  }

  data = {
    "documents": [{
      "id": id,
      "text": content,
    }]
  }
  response = requests.post(url, json=data, headers=headers, timeout=600)

  if response.status_code == 200:
    print("uploaded successfully.")
  else:
    print(f"Error: {response.status_code} {response.content}")


def query_database(query_prompt: str) -> Dict[str, Any]:
  """
  Query vector database to retrieve chunk with user's input question.
  """
  url = "http://0.0.0.0:8000/query"
  headers = {
    "Content-Type": "application/json",
    "accept": "application/json",
    "Authorization": f"Bearer {DATABASE_INTERFACE_BEARER_TOKEN}",
  }
  data = {"queries": [{"query": query_prompt, "top_k": SEARCH_TOP_K}]}

  response = requests.post(url, json=data, headers=headers, timeout=600)

  if response.status_code == 200:
    result = response.json()
    # process the result
    return result
  else:
    raise ValueError(f"Error: {response.status_code} : {response.content}")


if __name__ == "__main__":
  upsert_file("./data")
