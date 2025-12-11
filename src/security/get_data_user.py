from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException,status, Cookie
from sqlalchemy.orm import Session
from config import get_db
from .jwt import decode_access_token
from utils import get_by_username
from models import UserModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def get_current_user(access_token: str = Cookie(None), db:Session = Depends(get_db)) -> UserModel:
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )
    payload = decode_access_token(token=access_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )
    username = payload.get('sub')
    
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )
    user = get_by_username(db, username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='User not found'
        )
    
    return user