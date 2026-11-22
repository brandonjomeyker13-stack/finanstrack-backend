class AppError(Exception):
    """Error de negocio. main.py lo convierte en HTTP.

    Los services no importan FastAPI: lanzan esto y el marco web decide
    el código. `codigo` es para el front (no cambia); `message` es para
    la persona (sí puede cambiar).
    """

    def __init__(self, message: str, codigo: str | None = None):
        self.message = message
        self.codigo = codigo
        super().__init__(message)


class NotFoundError(AppError):
    """-> 404"""


class ConflictError(AppError):
    """-> 409"""


class UnauthorizedError(AppError):
    """-> 401"""


class ForbiddenError(AppError):
    """-> 403"""


class ValidationError(AppError):
    """-> 422"""
