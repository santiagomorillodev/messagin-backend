from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .base import Base
from dotenv import load_dotenv
import os
load_dotenv()
URL = os.getenv('DATABASE_URL')

if URL is None:
    raise ValueError('error connecting to the database ')
engine = create_engine(URL, pool_pre_ping=True, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)