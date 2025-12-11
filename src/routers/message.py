from fastapi import APIRouter, HTTPException, status, Depends, File, Form, UploadFile
from models import MessageModel, UserModel, ConversationModel, FollowerModel, NotificationModel, PostModel
from cloudinary import uploader
from schemas import MessageDelete, MessageCreate, MessageRead, MessageRequest, MessageResponse, ConversationRequest
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from config import get_db
from security import get_current_user


root = APIRouter(prefix="/inbox", tags=['Messages'])
        
        
@root.post('/')
def create_message(message: MessageCreate, current_user:UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        user_in_conversation = db.query(ConversationModel).filter(((ConversationModel.first_user_id == current_user.id)| (ConversationModel.second_user_id == current_user.id))).first()

        if not user_in_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You don't belong in that conversation."
            )
        conversation = db.query(ConversationModel).filter(ConversationModel.id == message.conversation_id).first()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='The conversations not exist'
            )
            
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid credentials'
            )
        
        new_message = MessageModel(
            sender_id = current_user.id,
            content = message.content,
            conversation_id=message.conversation_id
        )
        
        db.add(new_message)
        db.commit()
        return message
    except ValueError as error:
        print(error)
        

@root.post('/api/create/message')
async def create_post(
    conversation_id: int = Form(...),
    content: str = Form(None),
    file: UploadFile = File(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        image_url = None

        if file:
            result = uploader.upload(file.file)
            image_url = result.get('secure_url')

        # 🔹 Crear el nuevo mensaje
        new_message = MessageModel(
            sender_id=current_user.id,
            conversation_id=conversation_id,
            content=content,
            image_url=image_url,
        )

        db.add(new_message)
        db.commit()
        db.refresh(new_message)

        return {
            "message_id": new_message.message_id,
            "sender_id": new_message.sender_id,
            "conversation_id": new_message.conversation_id,
            "content": new_message.content,
            "image_url": new_message.image_url,
            "created": new_message.created.isoformat(),
            "status": new_message.status,
        }

    except Exception as e:
        print("⚠️ Error creando mensaje:", e)
        raise HTTPException(status_code=500, detail="Error creando mensaje")


@root.get('/chat/{id}', response_model=list[MessageResponse])
def get_messages(id: int, current_user:UserModel = Depends(get_current_user), db:Session = Depends(get_db)):
    try: 
        conversation_db = db.query(ConversationModel).filter(ConversationModel.id == id).first()
        if not conversation_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='The conversations not exist'
            )
        
        user = db.query(ConversationModel).filter(or_((ConversationModel.first_user_id == current_user.id), (ConversationModel.second_user_id == current_user.id))).all()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="You don't belong in that conversation."
            )
            
        print(id)
        
        messages = db.query(MessageModel).filter(MessageModel.conversation_id == id).all()
        
        print(messages)
        
        
        return messages
    except ValueError as error:
        print(error)
        
@root.delete('/message/delete/{message}')
def delete_message(message: int, current_user:UserModel = Depends(get_current_user), db:Session = Depends(get_db)):
    try:
        message_db = db.query(MessageModel).filter(((MessageModel.message_id == message) & (MessageModel.sender_id == current_user.id))).first()
        if not message_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Message not found'
            )
        
        db.delete(message_db)
        db.commit()
        return 'Message Deleted'
    except ValueError as error:
        print(error)
        
@root.post('/message/change-status/{conversation_id}')
def change_status(conversation_id: int, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        print('ok')
        conversation_db = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
        if not conversation_db:
            return
        db.query(MessageModel).filter(and_(MessageModel.sender_id != current_user.id, MessageModel.conversation_id == conversation_id)).update({MessageModel.status : True})
        db.commit()
        return 'User status changed'
        
        
    except ValueError as e:
        raise HTTPException (status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))