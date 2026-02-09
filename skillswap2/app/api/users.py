from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.utils.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


# ======================
# GET: Current user profile
# ======================
@router.get("/me")
def get_current_user_profile(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    base_info = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "name": current_user.name,  # From User model
        "profile": {
            "full_name": profile.full_name,
            "phone": profile.phone,
            "age": profile.age
        }
    }

    if current_user.role == "mentor":
        base_info["profile"]["qualification"] = profile.qualification
        base_info["profile"]["experience"] = profile.experience
    else:
        base_info["profile"]["college"] = profile.studying
        base_info["profile"]["what_to_learn"] = profile.bio

    return base_info


# ======================
# PUT: Update profile (both roles)
# ======================
@router.put("/profile")
def update_profile(
    full_name: str = Form(None),
    phone: str = Form(None),
    age: int = Form(None),
    # Mentor-specific
    qualification: str = Form(None),
    experience: str = Form(None),
    # Learner-specific
    studying: str = Form(None),
    bio: str = Form(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Update common fields
    if full_name is not None:
        profile.full_name = full_name
    if phone is not None:
        profile.phone = phone
    if age is not None:
        profile.age = age

    # Role-specific updates
    if current_user.role == "mentor":
        if qualification is not None:
            profile.qualification = qualification
        if experience is not None:
            profile.experience = experience
    else:  # learner
        if studying is not None:
            profile.studying = studying
        if bio is not None:
            profile.bio = bio

    db.commit()
    return {"message": "Profile updated successfully"}


# ======================
# PUT: Update password
# ======================
@router.put("/password")
def update_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.utils.security import verify_password, get_password_hash
    
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    return {"message": "Password updated successfully"}