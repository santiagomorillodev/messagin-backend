from sqlalchemy.orm import Session
from models import UserModel, LikeModel
from .follows import verify_follow



def get_user_email(db:Session, email:str) -> UserModel:
    return db.query(UserModel).filter(UserModel.email == email).first()

def get_by_username(db:Session, username:str) -> UserModel:
    return db.query(UserModel).filter(UserModel.username == username).first()

def get_user_by_id (current_user: UserModel, id: int, db:Session) -> dict:
    user = db.query(UserModel).filter(UserModel.id == id).first()
    if not user:
        raise ValueError('User not found')
    new_user = {
        "id": user.id,
        "name" : user.name,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "age": user.age,
        "email": user.email,
        "follows" : len(user.followers),
        "following" : verify_follow(current_user, id, db),
        "status": user.status,
        "created": user.created
    }
    return new_user

def user_like (user:UserModel, post: LikeModel):
    likes = user.likes
    for like in likes:
        if like['id'] == post.id:
            return True
    
    return False