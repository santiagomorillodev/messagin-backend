import os
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict):
    """Crea un JWT válido por 30 minutos."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    if not SECRET_KEY:
        raise ValueError('SECRET KEY NOT FOUND')
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, str]]:
    """Decodifica el JWT y devuelve el payload si es válido."""
    try:
        if not SECRET_KEY:
            raise ValueError('SECRET KEY NOT FOUND')
    
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as error:
        print("Token inválido:", error)
        return None
