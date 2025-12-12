from config import Base
from sqlalchemy import Column, Text, Integer, ForeignKey, func, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

class PostModel(Base):
    __tablename__ = 'Post'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user: Mapped[int] = mapped_column(Integer, ForeignKey('Users.id', ondelete='CASCADE'), nullable=False)
    public_id: Mapped[int] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship('UserModel', back_populates='posts')
    likes = relationship("LikeModel", back_populates="post", cascade="all, delete-orphan", passive_deletes=True)
