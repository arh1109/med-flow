from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.dependencies import get_db, get_current_user
from app.models import (
    DiagnosticLog,
    WorkOrder,
    User,
    UserRole,
)
from app.schemas.diagnostic_log import DiagnosticLogRead


router = APIRouter(
    prefix="/diagnostic_logs",
    tags=["diagnostic_logs"],
)


ALLOWED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------
# Local upload directory
#
# backend/uploads/diagnostics/
# ---------------------------------------------------------

UPLOAD_DIRECTORY = Path("uploads") / "diagnostics"


def can_upload_diagnostic(user: User) -> bool:
    return user.role in {
        UserRole.CLINICAL_ADMIN,
        UserRole.FIELD_TECHNICIAN,
    }


@router.get(
    "",
    response_model=list[DiagnosticLogRead],
)
async def list_diagnostic_logs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[DiagnosticLog]:

    statement = (
        select(DiagnosticLog)
        .order_by(DiagnosticLog.created_at.desc())
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


@router.post(
    "",
    response_model=DiagnosticLogRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_diagnostic_report(
    work_order_id: int = Form(...),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),

    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosticLog:

    # ---------------------------------------------------------
    # RBAC
    # ---------------------------------------------------------

    if not can_upload_diagnostic(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only Clinical Admins and Field Technicians "
                "may upload diagnostic reports"
            ),
        )

    # ---------------------------------------------------------
    # Make sure work order exists
    # ---------------------------------------------------------

    work_order = await db.get(
        WorkOrder,
        work_order_id,
    )

    if work_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work order {work_order_id} not found",
        )

    # ---------------------------------------------------------
    # Validate filename
    # ---------------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file type. "
                "Allowed: txt, pdf, png, jpg, jpeg, gif, webp"
            ),
        )

    # ---------------------------------------------------------
    # Read and validate file size
    # ---------------------------------------------------------

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Diagnostic report cannot exceed 10 MB",
        )

    # ---------------------------------------------------------
    # Create unique local filename
    #
    # uploads/
    #   diagnostics/
    #     12/
    #       <uuid>-inspection.pdf
    # ---------------------------------------------------------

    safe_filename = Path(file.filename).name

    stored_filename = f"{uuid4()}-{safe_filename}"

    work_order_directory = (
        UPLOAD_DIRECTORY / str(work_order_id)
    )

    file_path = (
        work_order_directory / stored_filename
    )

    # ---------------------------------------------------------
    # Create directory if it does not exist
    # ---------------------------------------------------------

    try:
        await run_in_threadpool(
            work_order_directory.mkdir,
            parents=True,
            exist_ok=True,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create diagnostic upload directory",
        ) from exc

    # ---------------------------------------------------------
    # Save file locally
    # ---------------------------------------------------------

    try:
        await run_in_threadpool(
            file_path.write_bytes,
            contents,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save diagnostic report",
        ) from exc

    # ---------------------------------------------------------
    # Store a local URI in PostgreSQL
    #
    # Example:
    # local://diagnostics/12/<uuid>-inspection.pdf
    # ---------------------------------------------------------

    relative_path = (
        Path("diagnostics")
        / str(work_order_id)
        / stored_filename
    )

    file_url = f"local://{relative_path.as_posix()}"

    # ---------------------------------------------------------
    # Create PostgreSQL row
    # ---------------------------------------------------------

    diagnostic_log = DiagnosticLog(
        work_order_id=work_order_id,
        file_url=file_url,
        notes=notes,
    )

    db.add(diagnostic_log)

    try:
        await db.commit()
        await db.refresh(diagnostic_log)

    except Exception:
        await db.rollback()

        # -----------------------------------------------------
        # DB failed after file was saved.
        # Delete the local file.
        # -----------------------------------------------------

        try:
            if file_path.exists():
                await run_in_threadpool(
                    file_path.unlink,
                )
        except Exception:
            pass

        raise

    return diagnostic_log


@router.get("/{diagnostic_log_id}/download")
async def download_diagnostic_report(
    diagnostic_log_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> FileResponse:

    # ---------------------------------------------------------
    # Find diagnostic log
    # ---------------------------------------------------------

    log = await db.get(
        DiagnosticLog,
        diagnostic_log_id,
    )

    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic log {diagnostic_log_id} not found",
        )

    # ---------------------------------------------------------
    # Verify local file location
    # ---------------------------------------------------------

    prefix = "local://diagnostics/"

    if not log.file_url.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Diagnostic report has an invalid local file location",
        )

    relative_path = log.file_url.removeprefix(
        "local://"
    )

    # relative_path:
    #
    # diagnostics/12/<uuid>-inspection.pdf

    file_path = Path("uploads") / relative_path

    # ---------------------------------------------------------
    # Make sure file still exists
    # ---------------------------------------------------------

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic report file could not be found",
        )

    # ---------------------------------------------------------
    # Return the actual file
    # ---------------------------------------------------------

    stored_filename = file_path.name

    # Remove the UUID prefix for the downloaded filename.
    #
    # UUIDs are 36 characters:
    #
    # xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx-filename.pdf
    #                                     ^
    #                                     37 chars including -
    #
    original_filename = (
        stored_filename[37:]
        if len(stored_filename) > 37
        else stored_filename
    )

    return FileResponse(
        path=file_path,
        filename=original_filename,
    )