from typing import Any, Dict
import requests
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel
import hashlib
import os
import configparser
import sys

# Get the home directory path
home_dir = os.path.expanduser("~")

# Config directory and file path
config_dir = os.path.join(home_dir, '.llama_index')
config_file = os.path.join(config_dir, 'config')

log_file = os.path.join(config_dir, 'watcher.log')
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s %(message)s')

# Check if the config file exists
if not os.path.exists(config_file):
  # If not, create the directory and file
  os.makedirs(config_dir, exist_ok=True)
  config = configparser.ConfigParser()
  config['DEFAULT'] = {
    'DATABASE_INTERFACE_BEARER_TOKEN': 'your_token_here',
    'LLAMA_INDEX_SERVER': 'your_server_here',
  }
  with open(config_file, 'w') as f:
    config.write(f)

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the config from the file
config.read(config_file)

DATABASE_INTERFACE_BEARER_TOKEN = config.get('DEFAULT', 'DATABASE_INTERFACE_BEARER_TOKEN')
LLAMA_INDEX_SERVER = config.get('DEFAULT', 'LLAMA_INDEX_SERVER')
BEARER_TOKEN = {"Authorization": "Bearer " + DATABASE_INTERFACE_BEARER_TOKEN}

HEADERS = {
  "accept": "application/json",
  "Content-Type": "application/json",
}
HEADERS.update(BEARER_TOKEN)
SEARCH_TOP_K = 3


class Source(str, Enum):
  email = "email"
  file = "file"
  chat = "chat"

class DocumentMetadata(BaseModel):
  source: Optional[Source] = None
  source_id: Optional[str] = None
  url: Optional[str] = None
  created_at: Optional[str] = None
  author: Optional[str] = None

def get_document_metadata(file_path: str, source: Source, author: Optional[str] = "") -> DocumentMetadata:
  """
  Get the metadata for a document.
  """
  # Get the last modification time of the file
  modification_time = os.path.getmtime(file_path)
  # Convert it to a datetime object
  modification_time = datetime.fromtimestamp(modification_time)
  # Format it as a string
  created_at = modification_time.isoformat()

  # Compute a SHA256 hash of the file path to use as the source_id
  source_id = hashlib.sha256(file_path.encode()).hexdigest()

  # Construct the DocumentMetadata object
  metadata = DocumentMetadata(
    source=source,
    source_id=source_id,
    url=file_path,
    created_at=created_at,
    author=author,
  )

  return metadata

def upsert_file(directory: str, source: Source, author: Optional[str] = ""):
  """
  Upload all files under a directory to the vector database.
  """
  logging.info(f"Started update for file {directory}")
  url = f"{LLAMA_INDEX_SERVER}/upsert-file"
  for root, dirs, files in os.walk(directory,  followlinks=True):
    for filename in files:
      file_path = os.path.join(root, filename)
      relative_path = os.path.relpath(file_path, directory)
      with open(file_path, "rb") as f:
        file_content = f.read()

      # Get metadata for the file
      metadata = get_document_metadata(file_path, source, author)

      # Convert the metadata object to a JSON string
      metadata_json = metadata.json()

      # Create a new list for each file
      file_list = [("file", (relative_path, file_content, "text/plain")),
                   ("metadata", (None, metadata_json, "application/json"))]

      response = requests.post(url, headers=BEARER_TOKEN, files=file_list, timeout=600)
      if response.status_code == 200:
        logging.info(relative_path + " uploaded successfully.")
      else:
        logging.error(f"Error: {response.status_code} {response.content} for uploading " + relative_path)


def upsert(id: str, content: str):
  """
  Upload one piece of text to the database.
  """
  url = f"{LLAMA_INDEX_SERVER}upsert"

  data = {
    "documents": [{
      "id": id,
      "text": content,
    }]
  }
  response = requests.post(url, json=data, headers=HEADERS, timeout=600)

  if response.status_code == 200:
    logging.info("uploaded successfully.")
  else:
    logging.error(f"Error: {response.status_code} {response.content}")


def query_database(query_prompt: str) -> Dict[str, Any]:
  """
  Query vector database to retrieve chunk with user's input question.
  """
  url = f"{LLAMA_INDEX_SERVER}/query"
  data = {"queries": [{"query": query_prompt, "top_k": SEARCH_TOP_K}]}

  response = requests.post(url, json=data, headers=HEADERS, timeout=600)

  if response.status_code == 200:
    result = response.json()
    logging.info(result)
    # process the result
    return result
  else:
    raise ValueError(f"Error: {response.status_code} : {response.content}")


if __name__ == "__main__":
  #logging.basicConfig(level=logging.INFO)
  upsert_file(sys.argv[1], Source.file, sys.argv[2])
