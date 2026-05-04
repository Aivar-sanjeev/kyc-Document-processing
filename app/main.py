import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.logging_safe import install_safe_logging
from app.pipeline.process import UnsupportedDocumentError, process_document_bytes
from app.schemas import ProcessErrorResponse
from app.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    install_safe_logging()
    yield


app = FastAPI(
    title="KYC Document Processing Pipeline",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/process")
async def process(file: UploadFile = File(...)):
    settings = get_settings()
    data = await file.read()
    max_b = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_b:
        raise HTTPException(status_code=413, detail="File too large")

    try:
        result = await process_document_bytes(
            settings,
            file_bytes=data,
            filename=file.filename,
        )
        return JSONResponse(content=result.model_dump())
    except UnsupportedDocumentError as e:
        body = ProcessErrorResponse(
            error="unsupported_document",
            detail=str(e),
        )
        return JSONResponse(status_code=422, content=body.model_dump())
    except RuntimeError as e:
        logger.error("configuration_error %s", str(e))
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("process_failed")
        raise HTTPException(status_code=500, detail="Processing failed") from e
