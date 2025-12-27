"""Authentication endpoints for testing and validation.

Note: This router is primarily for validating auth implementation.
It may be removed or modified after Epic 2 is complete.
"""

from fastapi import APIRouter

from vintagestory_api.middleware.auth import CurrentUser
from vintagestory_api.models.responses import ApiResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=ApiResponse)
async def get_current_user_info(current_user: CurrentUser) -> ApiResponse:
    """Return the current user's role based on their API key.

    This endpoint is protected and requires a valid API key.

    Returns:
        ApiResponse with the user's role (admin or monitor).
    """
    return ApiResponse(
        status="ok",
        data={"role": current_user},
    )
