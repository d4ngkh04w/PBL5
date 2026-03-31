from .base import APIError


class InvalidFileType(APIError):
    def __init__(self):
        super().__init__(
            message="Invalid file type",
            status_code=400,
        )


class UnsupportedMediaType(APIError):
    def __init__(self):
        super().__init__(
            message="Unsupported media type",
            status_code=415,
        )


class FileTooLarge(APIError):
    def __init__(self, max_size: int):
        super().__init__(
            message="File too large",
            status_code=413,
            details={"Max size": max_size},
        )


class InvalidImage(APIError):
    def __init__(self):
        super().__init__(
            message="Invalid image file",
            status_code=400,
        )


class ModelError(APIError):
    def __init__(self):
        super().__init__(
            message="Model inference failed",
            status_code=500,
        )


class Unauthorized(APIError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            status_code=401,
        )
