from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, ForeignKey, func, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from celery import Celery
import redis
import openai
from datetime import datetime
import os

# Database Configuration
DATABASE_URL = "sqlite:///reviews.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Celery Configuration
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
celery = Celery("tasks", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

# OpenAI Configuration
openai.api_key = os.getenv("sk-proj-WsIUETVdti5boS0gbz85P1I89a-EaCZn83vPhqsP792KYBqeiNUVor6XKyYdKrWsfcgwKf06NhHUvnpEQQ843EA")  # Make sure to set your OpenAI key in the environment

# Models
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    reviews = relationship("ReviewHistory", backref="category")


class ReviewHistory(Base):
    __tablename__ = "review_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, nullable=True)
    stars = Column(Float, nullable=False)
    review_id = Column(String, nullable=False)
    tone = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    text = Column(String, nullable=False)


# Create Tables
Base.metadata.create_all(engine)

# FastAPI App Configuration
app = FastAPI()

# CORS Middleware
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Models
class CategoryModel(BaseModel):
    id: int
    name: str
    description: str
    average_stars: float
    total_reviews: int

    class Config:
        from_attributes = True

class ReviewModel(BaseModel):
    id: int
    text: str
    stars: float
    review_id: str
    tone: str
    sentiment: str
    category_id: int
    created_at: str

    class Config:
        from_attributes = True


# Celery Tasks
@celery.task(name="log_access")
def log_access_task(text: str):
    db = SessionLocal()
    try:
        log = AccessLog(text=text)
        db.add(log)
        db.commit()
    finally:
        db.close()


# API Endpoints

@app.post("/add_sample_data/")
async def add_sample_data():
    db = SessionLocal()
    try:
        # Sample Categories
        category1 = Category(name="Electronics", description="All things related to electronics.")
        category2 = Category(name="Books", description="Wide range of books.")
        category3 = Category(name="Home Appliances", description="Appliances for your home.")
        db.add_all([category1, category2, category3])

        print(db.query(Category).all())
        db.commit()

        # Sample Reviews
        review1 = ReviewHistory(
            text="Great quality phone, loved the features!",
            stars=9,
            review_id="abc123",
            tone="positive",
            sentiment="positive",
            category_id=category1.id,
        )
        review2 = ReviewHistory(
            text="Not a great read, boring storyline.",
            stars=3,
            review_id="def456",
            tone="negative",
            sentiment="negative",
            category_id=category2.id,
        )
        review3 = ReviewHistory(
            text="Very useful, works well in the kitchen.",
            stars=8,
            review_id="ghi789",
            tone="positive",
            sentiment="positive",
            category_id=category3.id,
        )
        db.add_all([review1, review2, review3])
        db.commit()

        return {"message": "Sample data added successfully!"}
    finally:
        db.close()



@app.get("/test_data")
async def test_data():
    db = SessionLocal()
    try:
        categories = db.query(Category).all()
        reviews = db.query(ReviewHistory).all()
        
        return {
            "categories": [category.name for category in categories],
            "reviews": [review.text for review in reviews],
        }
    finally:
        db.close()


@app.get("/reviews/trends", response_model=list[CategoryModel])
async def get_trends():
    db = SessionLocal()
    try:
        trends = (
            db.query(
                Category,
                func.avg(ReviewHistory.stars).label("average_stars"),
                func.count(ReviewHistory.review_id).label("total_reviews"),
            )
            .join(ReviewHistory, Category.id == ReviewHistory.category_id)
            .group_by(Category.id)
            .order_by(desc("average_stars"))
            .limit(5)
            .all()
        )

        result = []
        for category, average_stars, total_reviews in trends:
            result.append({
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "average_stars": average_stars,
                "total_reviews": total_reviews,
            })

        celery.send_task("log_access", args=["GET /reviews/trends"])
        return result
    finally:
        db.close()


@app.get("/reviews/", response_model=list[ReviewModel])
async def get_reviews(category_id: int, page: int = 1):
    db = SessionLocal()
    try:
        page_size = 15
        offset = (page - 1) * page_size

        reviews = (
            db.query(ReviewHistory)
            .filter(ReviewHistory.category_id == category_id)
            .order_by(ReviewHistory.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        result = []
        for review in reviews:
            if not review.tone or not review.sentiment:
                response = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=f"Classify the tone and sentiment of this review: \"{review.text}\" with stars {review.stars}.",
                    max_tokens=50,
                )
                review.tone = response.choices[0].text.strip()
                review.sentiment = response.choices[0].text.strip()

            result.append(ReviewModel.from_orm(review))

        celery.send_task("log_access", args=[f"GET /reviews/?category_id={category_id}"])
        return result
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
