"""Rotas HTTP de login, identidade e logout."""

from contextlib import AbstractContextManager
from typing import Annotated

from app.repositories.users import UsersRepository
from app.schemas.auth import (
    AuthUser,
    ChangePasswordRequest,
    CreateUserRequest,
    LoginRequest,
)
from app.security.dependencies import (
    get_current_user,
    get_user_repository,
    require_admin_ti,
)
from app.security.tokens import COOKIE_NAME, TOKEN_LIFETIME_SECONDS, issue_token
from app.services.auth import (
    DuplicateEmail,
    InvalidCredentials,
    InvalidCurrentPassword,
    authenticate_user,
    change_own_password,
    create_user,
)
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import InterfaceError, OperationalError, TimeoutError

router = APIRouter()


@router.post(
    "/auth/login",
    response_model=AuthUser,
    responses={
        401: {"description": "Credenciais inválidas"},
        403: {"description": "Origem não autorizada"},
        503: {"description": "Autenticação ou PostgreSQL indisponível"},
        500: {"description": "Erro interno"},
    },
)
def login(
    body: LoginRequest,
    response: Response,
    repository_context: Annotated[
        AbstractContextManager[UsersRepository], Depends(get_user_repository)
    ],
) -> AuthUser:
    try:
        with repository_context as users:
            user = authenticate_user(users, body.email, body.senha)
        token = issue_token(user["id"])
        result = AuthUser.model_validate(user)
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail="Credenciais inválidas") from exc
    except (InterfaceError, OperationalError, TimeoutError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503, detail="Autenticação indisponível"
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=TOKEN_LIFETIME_SECONDS,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    return result


@router.get(
    "/auth/me",
    response_model=AuthUser,
    responses={
        401: {"description": "Sessão ausente, inválida ou expirada"},
        503: {"description": "Autenticação ou PostgreSQL indisponível"},
        500: {"description": "Erro interno"},
    },
)
def me(user: Annotated[dict[str, object], Depends(get_current_user)]) -> AuthUser:
    return AuthUser.model_validate(user)


@router.post(
    "/auth/logout",
    status_code=204,
    responses={
        401: {"description": "Sessão ausente, inválida ou expirada"},
        403: {"description": "Origem não autorizada"},
        503: {"description": "Autenticação ou PostgreSQL indisponível"},
        500: {"description": "Erro interno"},
    },
)
def logout(
    response: Response, _user: Annotated[dict[str, object], Depends(get_current_user)]
) -> None:
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=False,
        samesite="lax",
    )


@router.post(
    "/auth/users",
    response_model=AuthUser,
    status_code=201,
    responses={
        401: {"description": "Sessão ausente, inválida ou expirada"},
        403: {"description": "Perfil ou origem não autorizados"},
        409: {"description": "Email já cadastrado"},
        503: {"description": "PostgreSQL indisponível"},
        500: {"description": "Erro interno"},
    },
)
def register_user(
    body: CreateUserRequest,
    _admin: Annotated[dict[str, object], Depends(require_admin_ti)],
    repository_context: Annotated[
        AbstractContextManager[UsersRepository],
        Depends(get_user_repository, use_cache=False),
    ],
) -> AuthUser:
    try:
        with repository_context as users:
            created = create_user(
                users,
                nome=body.nome,
                email=body.email,
                perfil=body.perfil,
                senha=body.senha,
            )
        return AuthUser.model_validate(created)
    except DuplicateEmail as exc:
        raise HTTPException(status_code=409, detail="Email já cadastrado") from exc
    except (InterfaceError, OperationalError, TimeoutError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503, detail="Autenticação indisponível"
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc


@router.patch(
    "/auth/password",
    status_code=204,
    responses={
        400: {"description": "Senha atual inválida"},
        401: {"description": "Sessão ausente, inválida ou expirada"},
        403: {"description": "Origem não autorizada"},
        503: {"description": "PostgreSQL indisponível"},
        500: {"description": "Erro interno"},
    },
)
def change_password(
    body: ChangePasswordRequest,
    user: Annotated[dict[str, object], Depends(get_current_user)],
    repository_context: Annotated[
        AbstractContextManager[UsersRepository],
        Depends(get_user_repository, use_cache=False),
    ],
) -> None:
    try:
        with repository_context as users:
            change_own_password(users, user["id"], body.senha_atual, body.nova_senha)
    except InvalidCurrentPassword as exc:
        raise HTTPException(status_code=400, detail="Senha atual inválida") from exc
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail="Não autenticado") from exc
    except (InterfaceError, OperationalError, TimeoutError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503, detail="Autenticação indisponível"
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Erro interno") from exc
