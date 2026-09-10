from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import Optional
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.models.user import User, Passenger, UserRole
from app.models.driver import Driver
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user

def require_role(allowed_roles: list[UserRole]):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: required role {allowed_roles}, but user has role {current_user.role}"
            )
        return current_user
    return role_checker

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing email
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    
    user = User(
        email=req.email,
        phone=req.phone,
        full_name=req.full_name,
        hashed_password=get_password_hash(req.password),
        role=req.role,
        is_active=True
    )
    db.add(user)
    await db.flush()

    if req.role == UserRole.PASSENGER:
        commuter_code = f"ZO-{str(uuid.uuid4().int)[:4]}"
        passenger = Passenger(
            user_id=user.id,
            commuter_id=commuter_code,
            total_trips=0
        )
        db.add(passenger)
    elif req.role == UserRole.DRIVER:
        from app.models.driver import Driver, DriverStatus, KYCStatus
        driver_code = f"DRV-{str(uuid.uuid4().int)[:4]}"
        driver = Driver(
            user_id=user.id,
            driver_code=driver_code,
            commercial_badge=f"TS-BG-{str(uuid.uuid4().int)[:5]}",
            license_number=f"TS-DL-{str(uuid.uuid4().int)[:6]}",
            status=DriverStatus.OFFLINE,
            kyc_status=KYCStatus.PENDING,
            experience_years=3,
            aadhaar_verified=True,
            police_cleared=True
        )
        db.add(driver)

    await db.commit()
    await db.refresh(user)

    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        role=user.role.value,
        full_name=user.full_name
    )

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    login_id = (req.identifier or req.username or req.email or "").strip()
    if not login_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email, phone, or Driver ID is required"
        )
    
    # Check by email or phone
    result = await db.execute(
        select(User).where(or_(User.email.ilike(login_id), User.phone == login_id))
    )
    user = result.scalar_one_or_none()

    # If not found by direct email/phone, check if identifier is a driver_code
    if not user:
        drv_res = await db.execute(select(Driver).where(Driver.driver_code.ilike(login_id)))
        drv = drv_res.scalar_one_or_none()
        if drv:
            u_res = await db.execute(select(User).where(User.id == drv.user_id))
            user = u_res.scalar_one_or_none()

    # If still not found, check if identifier is a commuter_id
    if not user:
        pax_res = await db.execute(select(Passenger).where(Passenger.commuter_id.ilike(login_id)))
        pax = pax_res.scalar_one_or_none()
        if pax:
            u_res = await db.execute(select(User).where(User.id == pax.user_id))
            user = u_res.scalar_one_or_none()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your username/password."
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(subject=user.id, role=user.role.value)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        role=user.role.value,
        full_name=user.full_name
    )

@router.post("/logout")
async def logout():
    return {"status": "success", "message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
