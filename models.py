from sqlalchemy import Column, Integer, String, Text, ForeignKey
from db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    email = Column(String(100), unique=True)
    password = Column(String(255))


class Reports(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    file_name = Column(String(255))

    # NEW
    file_path = Column(String(500))

    resume_text = Column(Text)
    result = Column(Text)