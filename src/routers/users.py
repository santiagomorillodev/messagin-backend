from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, desc
from schemas import UserCreate,UserRead,UserDeleteRequest,UserUpdate,UserLikes, UserPassword, UserEmail, UserReadMe
from models import UserModel, FollowerModel, LikeModel, RecentModel,PostModel, NotificationModel
from utils import get_user_email, get_by_username, verify_follow, get_user_by_id
from config import get_db
from security import hash_password, verify_password, create_access_token, get_current_user
from datetime import datetime, timedelta
from cloudinary import uploader, api

root = APIRouter(tags=["Users"])


@root.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    email = get_user_email(db, user.email)
    user_username = get_by_username(db, user.username)
    if email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "The email is already in use"},
        )

    if user_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "The username is already in use"},
        )

    new_user = UserModel(
        name=user.name,
        age=user.age,
        email=user.email,
        username=user.username,
        password=hash_password(user.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User Created"}


@root.post('/login')
def login(data:OAuth2PasswordRequestForm = Depends(), db:Session = Depends(get_db)):
    
    try:
        user_db = db.query(UserModel).filter(UserModel.username == data.username).first()
        
        if not user_db or not verify_password(data.password, user_db.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='invalid credentials'
            )
            
        token = create_access_token({'sub': user_db.username, 'id': user_db.id})
        
        response = JSONResponse(content={'message': 'Login successful'})
        response.set_cookie(
            key='access_token',
            value=token,
            httponly=False,
            samesite='lax',
            secure=False,
            max_age=1800,
            expires=1800
        )
        db.query(UserModel).filter(UserModel.id == user_db.id).update({UserModel.status: True})
        db.commit()
        db.refresh(user_db)
        print(user_db.status)
        return response
    
    except ValueError as error:
        print(error)


@root.post('/logout')
def logout (current_user: UserModel = Depends(get_current_user), db:Session = Depends(get_db)):
    try:
        user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
        db.query(UserModel).filter(UserModel.id == user.id).update({UserModel.status: False})
        db.commit()
        db.refresh(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@root.get("/", response_model=list[UserRead])
def get_users(db: Session = Depends(get_db)):
    users = db.query(UserModel).all()
    return users


@root.get("/id/{id}", response_model=UserRead)
def get_user(id: int, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    user = get_user_by_id(current_user, id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "User not found"},
        )
    return user


@root.get("/search/username/{username}", response_model=UserRead)
def get_username(username: str, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current_username = str(current_user.username)
        if current_username == username:
            raise HTTPException (status_code=status.HTTP_409_CONFLICT, detail='User not found')
        user = get_by_username(db, username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "User not found"},
            )

        recent = db.query(RecentModel).filter(
            and_(
                RecentModel.user_id == current_user.id,
                RecentModel.other_user == user.id
            )
        ).first()

        if not recent:
            # 👇 Si no existe, crear nuevo
            new_search = RecentModel(user_id=current_user.id, other_user=user.id)
            db.add(new_search)
        else:
            # 👇 Si ya existe, solo actualiza la fecha
            db.query(RecentModel).filter(RecentModel.user_id == current_user.id).update({RecentModel.created: datetime.utcnow()})

        db.commit()
        return user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

        
@root.get("/me", response_model=UserReadMe)
def current_user(user: UserModel = Depends(get_current_user)):
    return user

@root.delete("/delete/account")
def delete_current_user(data: UserDeleteRequest, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.email != data.email:
        print('invalid email')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials in endpoint",
        )
    password = str(data.password)
    correct_password = verify_password(password, user.password)

    if not correct_password:
        print('invalid password')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials in endpoint",
        )

    db.delete(user)
    db.commit()
    return {"message": "deleted"}


from fastapi import UploadFile, File, Form

@root.patch("/update")
async def update_user(
    name: str = Form(None),
    username: str = Form(None),
    email: str = Form(None),
    password: str = Form(None),
    description: str = Form(None),

    avatar: UploadFile = File(None),
    banner: UploadFile = File(None),

    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # ------------------------------
    # ⚡ UPDATE TEXT FIELDS
    # ------------------------------
    if name:
        current_user.name = name

    if username:
        current_user.username = username

    if email:
        current_user.email = email

    if description:
        current_user.description = description

    if password:
        current_user.password = hash_password(password)

    # ------------------------------
    # ⚡ UPDATE AVATAR
    # ------------------------------
    if avatar:
        # eliminar avatar anterior si existe
        if current_user.avatar_public_id:
            uploader.destroy(current_user.avatar_public_id)

        upload_result = uploader.upload(avatar.file)
        current_user.avatar_url = upload_result.get("secure_url")
        current_user.avatar_public_id = upload_result.get("public_id")

    # ------------------------------
    # ⚡ UPDATE BANNER
    # ------------------------------
    if banner:
        if current_user.banner_public_id:
            uploader.destroy(current_user.banner_public_id)

        upload_result = uploader.upload(banner.file)
        current_user.banner_url = upload_result.get("secure_url")
        current_user.banner_public_id = upload_result.get("public_id")

    # ------------------------------
    # ⚡ SAVE CHANGES
    # ------------------------------
    db.commit()
    db.refresh(current_user)

    return {"message": "User updated successfully"}




@root.patch('/change/password')
def change_password(data:UserPassword, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user = db.query(UserModel).filter(UserModel.id == user.id).first()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    new_password = hash_password(data.new_password)
    db.query(UserModel).filter(UserModel.id == current_user.id).update({UserModel.password: new_password})
    db.commit()
    db.refresh(current_user)
    return {"message": "Updated user"}


@root.get('/change/email')
def change_email(data:UserEmail, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user = db.query(UserModel).filter(UserModel.id == user.id).first()
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    if not verify_password(data.current_password, current_user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    db.query(UserModel).filter(UserModel.id == current_user.id).update({UserModel.email: data.email})
    db.commit()
    db.refresh(current_user)
    return {"message": "Updated user"}


@root.get("/recent/search", response_model=list[UserRead])
def get_recent_search(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        recent_searches = (db.query(RecentModel).filter(RecentModel.user_id == current_user.id).order_by(RecentModel.created.desc()).all())
        users = [get_user_by_id(current_user, r.other_user, db) for r in recent_searches if get_user_by_id(current_user, r.other_user, db)]
        return users

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@root.delete('/recent/search/{id}')
def delete_recent_search(
    id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        recent = db.query(RecentModel).filter(and_((RecentModel.user_id == current_user.id),(RecentModel.other_user == id))).one_or_none()
        print(recent, id)
        if not recent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recent search not found"
            )

        db.delete(recent)
        db.commit()
        return {"message": "Recent search deleted"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@root.get("/followers")
def get_follower(user: UserModel = Depends(get_current_user)):
    if not user or not user.followers:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "He has no followers"})
    return user.followers


@root.get("/following")
def get_followed(user: UserModel = Depends(get_current_user)):
    if not user or not user.following:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "You don't follow anyone"})
    return user.following


@root.post("/api/follow/{followed}")
async def toggle_follow(
    followed: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # No puede seguirse a sí mismo
    if followed == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself"
        )

    # Verificar si ya existe follow
    exist_follow = (
        db.query(FollowerModel)
        .filter(
            and_(
                FollowerModel.follower_id == current_user.id,
                FollowerModel.followed_id == followed
            )
        )
        .first()
    )

    # Si ya existe → UNFOLLOW
    if exist_follow:
        db.delete(exist_follow)
        db.commit()
        following = False
    else:
        # Crear FOLLOW
        new_follow = FollowerModel(
            follower_id=current_user.id,
            followed_id=followed
        )
        db.add(new_follow)

        # Notificación
        new_notification = NotificationModel(
            user_id=followed,
            other_user_id=current_user.id,
            content="¡Te ha comenzado a seguir!"
        )
        db.add(new_notification)
        db.commit()
        following = True

    # Obtener número actualizado de followers
    follows_count = (
        db.query(FollowerModel)
        .filter(FollowerModel.followed_id == followed)
        .count()
    )

    return {
        "following": following,   # true/false
        "follows": follows_count  # número actualizado
    }




@root.delete("/follower")
def unfollow(followed: int, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    following = verify_follow(current_user, followed, db)
    if not following:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"message": "You don't follow this account"})
    db.delete(following)
    db.commit()
    return {"message": "200 ok"}


@root.get("/likes")
async def get_likes(user: UserModel = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user.likes


@root.get('/post/all')
def get_user_post_all(
    user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid credentials'
        )

    try:
        # Tiempo límite: hace 24 horas
        time_limit = datetime.utcnow() - timedelta(hours=24)

        following_ids = (
            db.query(FollowerModel.followed_id)
            .filter(FollowerModel.follower_id == user.id)
            .subquery()
        )

        posts = (
            db.query(PostModel)
            .filter(
                and_(
                    (PostModel.id_user == user.id) |
                    (PostModel.id_user.in_(following_ids)),
                    PostModel.created >= time_limit            # 👈 FILTRO NUEVO
                )
            )
            .options(
                joinedload(PostModel.user),
                joinedload(PostModel.likes)
            )
            .order_by(PostModel.id.desc())
            .all()
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
        
@root.post("/api/like")
async def toggle_likes(post: UserLikes, user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)):
    post_db = db.query(PostModel).filter(PostModel.id == post.post_id).first()
    if not post_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    exist_like = db.query(LikeModel).filter(and_(LikeModel.user_id == user.id, LikeModel.post_id == post.post_id)).first()

    if exist_like:
        db.delete(exist_like)
        db.commit()
    else:
        new_like = LikeModel(user_id=user.id, post_id=post.post_id)
        db.add(new_like)
        db.commit()
    
    following_ids = db.query(FollowerModel.followed_id).filter(FollowerModel.follower_id == user.id).all()
    for id in following_ids:
        followed_id = id[0]
        new_notification = NotificationModel(
            user_id = followed_id,
            other_user_id = user.id,
            content = 'Le ha dado like a tu post!'
        )
        if new_notification:
            db.add(new_notification)
            db.commit()
    return status.HTTP_200_OK

@root.get('/notifications')
def get_notifications(
    current_user: UserModel = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    try:
        user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail='Invalid credentials'
            )
        
        notifications = (
            db.query(NotificationModel)
            .filter(NotificationModel.user_id == user.id)
            .order_by(NotificationModel.created.desc())
            .all()
        )

        if not notifications:
            return []  # <- No errors, just return empty list

        data = []
        for notification in notifications:
            other = (
                db.query(UserModel)
                .filter(UserModel.id == notification.other_user_id)
                .first()
            )
            
            if not other:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Other user not found')

            formatted = {
                'id': notification.id,
                "from_user_id": other.id,
                "username": other.username,
                "name": other.name,
                "avatar_url": other.avatar_url,
                "content": notification.content,
                "created": notification.created
            }

            data.append(formatted)

        return data

    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error: {str(e)}"
        )

@root.delete('/api/notification/delete/{id}')
def delete_notification(
    id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        notification = db.query(NotificationModel).filter(and_((NotificationModel.user_id == current_user.id),(NotificationModel.id == id))).one_or_none()
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )

        db.delete(notification)
        db.commit()
        return {"message": "Notification deleted"}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )