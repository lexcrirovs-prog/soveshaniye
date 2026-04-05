import io
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SalesScript
from app.schemas import SalesScriptCreate, SalesScriptOut, SalesScriptUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scripts", tags=["scripts"])


def extract_text_from_file(file: UploadFile) -> tuple[str, str]:
    """Extract text from uploaded file (PDF, DOCX, TXT)."""
    content = file.file.read()
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "txt":
        return content.decode("utf-8", errors="replace"), "txt"

    elif ext == "pdf":
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts), "pdf"

    elif ext in ("docx", "doc"):
        from docx import Document

        doc = Document(io.BytesIO(content))
        text_parts = [p.text for p in doc.paragraphs]
        return "\n".join(text_parts), "docx"

    else:
        # Try as plain text
        try:
            return content.decode("utf-8", errors="replace"), "txt"
        except Exception:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")


@router.get("", response_model=list[SalesScriptOut])
def list_scripts(db: Session = Depends(get_db)):
    """List all sales scripts."""
    return db.query(SalesScript).order_by(SalesScript.created_at.desc()).all()


@router.post("", response_model=SalesScriptOut)
def create_script(
    name: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(None),
    content: str = Form(None),
    db: Session = Depends(get_db),
):
    """Create a new sales script (from file or text)."""
    script_content = ""
    file_type = None
    original_file = None

    if file:
        script_content, file_type = extract_text_from_file(file)
        original_file = file.filename
    elif content:
        script_content = content
        file_type = "txt"
    else:
        raise HTTPException(status_code=400, detail="Provide either file or content")

    script = SalesScript(
        name=name,
        description=description,
        content=script_content,
        original_file=original_file,
        file_type=file_type,
    )
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


@router.get("/{script_id}", response_model=SalesScriptOut)
def get_script(script_id: int, db: Session = Depends(get_db)):
    """Get a sales script by ID."""
    script = db.query(SalesScript).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@router.put("/{script_id}", response_model=SalesScriptOut)
def update_script(script_id: int, data: SalesScriptUpdate, db: Session = Depends(get_db)):
    """Update a sales script."""
    script = db.query(SalesScript).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    if data.name is not None:
        script.name = data.name
    if data.description is not None:
        script.description = data.description
    if data.content is not None:
        script.content = data.content
    if data.is_active is not None:
        # Deactivate all others if activating this one
        if data.is_active:
            db.query(SalesScript).filter(SalesScript.id != script_id).update({"is_active": False})
        script.is_active = data.is_active

    db.commit()
    db.refresh(script)
    return script


@router.delete("/{script_id}")
def delete_script(script_id: int, db: Session = Depends(get_db)):
    """Delete a sales script."""
    script = db.query(SalesScript).get(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    db.delete(script)
    db.commit()
    return {"status": "deleted"}
