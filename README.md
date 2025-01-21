# FastAPI Project with Celery and Redis

This project demonstrates how to integrate FastAPI, Celery, and Redis to build a web API with background task processing.

## Features:
- FastAPI RESTful API to manage reviews, categories, and access logs.
- Celery for handling background tasks like logging access.
- Redis as the message broker and result backend for Celery.
- SQLite as the database for storing reviews, categories, and access logs.

## Setup Instructions:

### 1. Install Dependencies:
Make sure you have Python 3.7 or higher installed. Then, install the dependencies using pip:

```bash
pip install -r requirements.txt
