from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me")
def read_users_me():
    return {"message": "User endpoint working"}
