from sqlmodel import Session, SQLModel, create_engine
from typing import Generator
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
from schema import air_quality_schema,station_schema
import os

# Load environment variables from .env file
load_dotenv()

# PostgreSQL configuration
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")  # default postgres port
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")

# URL-encode the password
encoded_password = quote_plus(POSTGRES_PASSWORD)
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{encoded_password}@{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    # pool_size=20,  # Connection pool size
    # max_overflow=10,  # Additional connections allowed beyond pool_size
    # pool_pre_ping=True,  # Test connections for health before use
    echo=True  # Log SQL queries (useful for development)
)

# Function to create database tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Dependency to get DB session
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session