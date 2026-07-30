"""认证领域服务。"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateUsernameError, InvalidCredentialsError
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(
        self,
        db: AsyncSession,
        user_repository: UserRepository | None = None,
    ) -> None:
        self.db = db
        self.users = user_repository or UserRepository(db)

    async def login(self, request: LoginRequest) -> TokenResponse:
        user = await self.users.get_by_username(request.username)
        if not user or not verify_password(request.password, user.password_hash):
            raise InvalidCredentialsError()

        token = create_access_token(
            {"user_id": user.id, "username": user.username, "role": user.role}
        )
        return TokenResponse(
            access_token=token, username=user.username, role=user.role
        )

    async def register(self, request: RegisterRequest) -> None:
        if await self.users.get_by_username(request.username):
            raise DuplicateUsernameError()

        try:
            await self.users.create(
                username=request.username,
                password_hash=hash_password(request.password),
            )
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise DuplicateUsernameError() from exc
