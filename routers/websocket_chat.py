from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from models import ConversationModel, MessageModel
from utils import upload_base64_to_cloudinary, save_message_to_db
from sockets import ConnectionManager
from config import get_db
import json

router = APIRouter(prefix="/ws", tags=["WebSocket"])

manager = ConnectionManager()

def get_unread_count(db, user_id: int):
    rows = db.execute(
        select(
            MessageModel.conversation_id,
            func.count().label("unread")
        )
        .where(
            MessageModel.sender_id != user_id,
            MessageModel.status == False
        )
        .group_by(MessageModel.conversation_id)
    ).all()

    return { row.conversation_id: row.unread for row in rows }



@router.websocket("/user/{user_id}")
async def user_socket(websocket: WebSocket, user_id: int, db: Session = Depends(get_db)):
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            
            raw = await websocket.receive_json()
            
            data = json.loads(raw)

            sender_id = data.get("sender_id")
            conversation_id = data.get("conversation_id")
            content = data.get("content")
            recipient_id = data.get("recipient_id")
            base64_image = data.get("image_base64")
            
            if data.get("type") == "call-offer":
                await manager.send_personal_message(
                    {
                        "type": "call-offer",
                        "from": sender_id,
                        "conversation_id": conversation_id,
                        "offer": data["offer"],
                    },
                    recipient_id
                )
                continue

            if data.get("type") == "call-answer":
                await manager.send_personal_message(
                    {
                        "type": "call-answer",
                        "from": sender_id,
                        "conversation_id": conversation_id,
                        "answer": data["answer"],
                    },
                    recipient_id
                )
                continue

            if data.get("type") == "ice-candidate":
                await manager.send_personal_message(
                    {
                        "type": "ice-candidate",
                        "from": sender_id,
                        "conversation_id": conversation_id,
                        "candidate": data["candidate"],
                    },
                    recipient_id
                )
                continue


            if not sender_id or not conversation_id:
                await websocket.send_json({
                    "error": "sender_id and conversation_id required"
                })
                continue

            # =========================================================
            # 1. VALIDAR QUE LA CONVERSACIÓN EXISTA
            # =========================================================
            conversation = db.query(ConversationModel).filter(
                ConversationModel.id == conversation_id
            ).first()

            if not conversation:
                await websocket.send_json({
                    "error": "Conversation does not exist."
                })
                continue

            if sender_id not in [conversation.first_user_id, conversation.second_user_id]:
                await websocket.send_json({
                    "error": "You do not belong to this conversation."
                })
                continue

            # =========================================================
            # 2. CLOUDINARY (opcional si se envía imagen)
            # =========================================================
            image_url = None
            public_id = None

            if base64_image:
                try:
                    uploaded = await upload_base64_to_cloudinary(base64_image)
                    image_url = uploaded["secure_url"]
                    public_id = uploaded["public_id"]
                except Exception as e:
                    await websocket.send_json({
                        "error": "Error uploading image to Cloudinary",
                        "details": str(e)
                    })
                    continue

            # =========================================================
            # 3. GUARDAR MENSAJE EN BD
            # =========================================================
            saved_message = await save_message_to_db(
                sender_id=sender_id,
                conversation_id=conversation_id,
                content=content,
                image_url=image_url,
                public_id=public_id,
                database=db
            )

            # =========================================================
            # 4. BROADCAST A TODOS LOS SOCKETS
            # =========================================================
            outgoing = {
                "type": "message",
                "sender_id": sender_id,
                "conversation_id": conversation_id,
                "content": saved_message.content,
                "image_url": saved_message.image_url,
                "public_id": saved_message.public_id,
                "created": saved_message.created.isoformat(),
            }

            await manager.broadcast(outgoing)

            # =========================================================
            # 5. NOTIFICACIÓN AL OTRO USUARIO
            # =========================================================
            if recipient_id and recipient_id != sender_id:
                notification = {
                    "type": "notification",
                    "recipient_id": recipient_id,
                    "conversation_id": conversation_id,
                    "title": "Nuevo mensaje",
                    "body": f"Usuario {sender_id} te ha enviado un mensaje.",
                    "timestamp": saved_message.created.isoformat(),
                }

                await manager.send_personal_message(notification, recipient_id)
                new_unread_map = get_unread_count(db, recipient_id)

                await manager.send_personal_message(
                    {
                        "type": "unread_update",
                        "unread": new_unread_map
                    },
                    recipient_id
                )

    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
