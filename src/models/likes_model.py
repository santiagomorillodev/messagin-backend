from config import Base
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime

class LikeModel(Base):
    __tablename__ = 'Likes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('Users.id', ondelete='CASCADE'), nullable=False)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey('Post.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),
    )

    user = relationship("UserModel", back_populates="likes")
    post = relationship("PostModel", back_populates="likes")
