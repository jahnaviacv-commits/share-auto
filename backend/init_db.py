import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.database import sync_engine, Base
import app.models  # load all models into Base.metadata

def init_database():
    print("Creating all database tables in PostgreSQL zeroone_db...")
    Base.metadata.create_all(bind=sync_engine)
    print("All tables successfully created!")

if __name__ == "__main__":
    init_database()
