from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import Base
from dotenv import load_dotenv
import os

load_dotenv()

URL = os.getenv('DATABASE_URL')
print(URL)

if URL is None:
    raise ValueError('Error connecting to the database')

connect_args = {}

if URL.startswith("mysql"):
    ca_path = os.path.abspath("certs/ca.pem")
    if os.path.exists(ca_path):
        connect_args = {
            "ssl": {
                "ca": ca_path
            }
        }
    else:
        raise ValueError(f"CA file not found at: {ca_path}")

elif URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
