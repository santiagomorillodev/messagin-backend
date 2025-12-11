from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException,status
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload
from models import PostModel, UserModel, FollowerModel, NotificationModel, LikeModel
from config import get_db
from security import get_current_user
from cloudinary import uploader, api

root = APIRouter(prefix='/post', tags=['Post'])

@root.post('/create')
async def create_post(
    content: str = Form(...),
    file: UploadFile = File(None),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        image_url = None
        public_id = None
        print(file)

        if file:
            result = uploader.upload(file.file)
            image_url = result.get('secure_url')
            public_id = result.get('public_id')

        post = PostModel(
            id_user=current_user.id,
            content=content,
            url=image_url,
            public_id=public_id
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        
        following_ids = db.query(FollowerModel.followed_id).filter(FollowerModel.follower_id == current_user.id).all()
        for id in following_ids:
            followed_id = id[0]
            new_notification = NotificationModel(
                user_id = followed_id,
                other_user_id = current_user.id,
                content = 'ha subido un nuevo post!'
            )
            if new_notification:
                db.add(new_notification)
                db.commit()

        

        return {
            "id": post.id,
            "content": post.content,
            "url": post.url,
            "public_id": post.public_id,
            "created": post.created
        }

    except Exception as e:
        print("⚠️ Error subiendo post:", e)
        raise HTTPException(status_code=500, detail="Error creating post")

@root.get('/{id}')
def get_posts_current_user(id: int, db: Session = Depends(get_db)):
    try:
        posts = (
            db.query(PostModel)
            .filter(PostModel.id_user == id)
            .options(
                joinedload(PostModel.user),
                joinedload(PostModel.likes)
            )
            .order_by(PostModel.id.desc())
            .all()
        )

        if not posts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Posts not found"
            )
        response = []
        for p in posts:
            response.append({
                "id": p.id,
                "content": p.content,
                "url": p.url,
                "public_id": p.public_id,
                "created": p.created,
                "likes": [{"user_id": l.user_id} for l in p.likes],
                "user": {
                    "user_id": p.user.id,
                    "username": p.user.username,
                    "name": p.user.name,
                    "avatar_url": p.user.avatar_url
                }
            })

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )



@root.delete('/delete/{id}')
async def delete_image(id: str ,current_user:UserModel = Depends(get_current_user), db:Session = Depends(get_db)):
    try:
        post = db.query(PostModel).filter(((PostModel.id_user == current_user.id) & (PostModel.id == id))).first()
        if not post:
            raise HTTPException(status_code=404, detail="Image not found or already deleted")
        
        if post.public_id:
        
            public_id = post.public_id
            
            image_cloudinary = api.resource(public_id)
            
            if not image_cloudinary:
                raise HTTPException(status_code=404, detail="Image not found or already deleted")
            
            result = uploader.destroy(public_id)
            
            if result.get("result") != "ok":
                raise HTTPException(status_code=404, detail="Image not found or already deleted")
        
        db.delete(post)
        db.commit()
        
        return {"message": "Post deleted successfully", "id": id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))