import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import jwt  # ← PyJWT, NO jose
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError, DecodeError

load_dotenv()

# VALIDAR que SECRET_KEY existe
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ ERROR CRÍTICO: SECRET_KEY no encontrada en .env")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict) -> str:
    """Crea un JWT válido por 30 minutos."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Payload estándar JWT
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),  # issued at
        "type": "access"
    })
    
    # 🔥 PyJWT.encode() - parámetros correctos
    encoded_jwt = jwt.encode(
        payload=to_encode,
        key=SECRET_KEY,
        algorithm=ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica el JWT y devuelve el payload si es válido."""
    try:
        payload = jwt.decode(
            jwt=token,
            key=SECRET_KEY,
            algorithms=[ALGORITHM],
            options={
                "verify_exp": True,
                "verify_signature": True
            }
        )
        return payload
    except ExpiredSignatureError:
        print("❌ Token expirado")
        return None
    except DecodeError:
        print("❌ Error decodificando token")
        return None
    except InvalidTokenError:
        print("❌ Token inválido")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None