class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400, data: dict | list | None = None):
        self.message = message
        self.status_code = status_code
        self.data = data

class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)

class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)

class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists", data: dict | list | None = None):
        super().__init__(message, status_code=409, data=data)

class InternalServerError(AppException):
    def __init__(self, message: str = "Internal Server Error"):
        super().__init__(message, status_code=500)