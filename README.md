# FastAPI Project with Celery and Redis

This project demonstrates how to integrate FastAPI, Celery, and Redis to build a web API with background task processing.

## Features:
- FastAPI RESTful API to manage reviews, categories, and access logs.
- Celery for handling background tasks like logging access.
- Redis as the message broker and result backend for Celery.
- SQLite as the database for storing reviews, categories, and access logs.

## Setup Instructions:

### 1. Install Dependencies:
### 2. To run Fast API App: uvicorn 1:app --reload
### 3. Start redis server. Command: (redis-server)
### 4. Start Celery Worker. Command: (celery -A 1.celery worker --loglevel=info)

## Note: Here I used a dummy API key for security purposes.

Make sure you have Python 3.7 or higher installed. Then, install the dependencies using pip:

```bash
pip install -r requirements.txt
