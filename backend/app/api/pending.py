from app.core.errors import AppError


def feature_not_ready() -> None:
    """계약만 준비된 API임을 한 가지 형식으로 알린다."""
    raise AppError(501, "feature_not_ready", "이 기능은 다음 단계에서 구현됩니다.")
