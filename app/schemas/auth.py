from pydantic import BaseModel, EmailStr, Field


class RegistroIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20)


class GoogleIn(BaseModel):
    credential: str = Field(min_length=20)


class BorrarCuentaIn(BaseModel):
    confirmacion: str = Field(min_length=1, max_length=20)


class UsuarioOut(BaseModel):
    id: str
    nombre: str
    email: EmailStr
    onboarding_completo: bool


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut
