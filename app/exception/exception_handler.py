import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exception.exceptions import (
    AuthenticationFailedException,
    EmailAttachmentException,
    IdTranslationException,
    FolderException,
    EmailException,
    GraphResponseException,
)

logger = logging.getLogger(__name__)

app = FastAPI()

async def authentication_exception_handler(request: Request, exc: AuthenticationFailedException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "failed",
            "type": "authentication_error",
            "detail": exc.detail,
            "path": str(request.url),
        },
    )

async def email_exception_handler(request: Request, exc: EmailException):
    logger.error("Email error on %s: %s, Folder: %s, Message ID: %s", request.url, exc.detail, exc.folder_name, exc.message_id)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "failed",
            "type": "email_error",
            "detail": exc.detail,
            "path": str(request.url),
            "folder_name": exc.folder_name,
            "message_id": exc.message_id,
        },
    )

async def attachment_exception_handler(request: Request, exc: EmailAttachmentException):
    logger.error("Attachment error on %s: %s, Attachment ID: %s", request.url, exc.detail, exc.attachment_id)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "failed",
            "type": "attachment_error",
            "detail": exc.detail,
            "path": str(request.url),
            "attachment_id": exc.attachment_id,
        },
    )

async def id_translation_exception_handler(request: Request, exc: IdTranslationException):
    logger.error("ID translation error on %s: %s, Source IDs: %s", request.url, exc.detail, exc.source_ids)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "failed",
            "type": "id_translation_error",
            "detail": exc.detail,
            "path": str(request.url),
            "source_ids": exc.source_ids,
        },
    )

async def folder_exception_handler(request: Request, exc: FolderException):
    logger.error("Folder error on %s: %s", request.url, exc.detail)
    content = {
        "status": "failed",
        "type": "folder_error",
        "detail": exc.detail,
        "path": str(request.url),
    }
    if exc.folder_name:
        content["folder_name"] = exc.folder_name
    if exc.folder_id:
        content["folder_id"] = exc.folder_id
    return JSONResponse(status_code=exc.status_code, content=content)

async def graph_response_exception_handler(request: Request, exc: GraphResponseException):
    logger.error("Graph response error on %s: %s", request.url, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "failed",
            "type": "graph_response_error",
            "detail": exc.detail,
            "path": str(request.url),
            "response_type": exc.response_type,
        },
    )

async def global_exception_handler(request: Request, exc: Exception):
    stack_trace = traceback.format_exc()
    logger.error("Unhandled exception on %s\nError: %s\nStack trace:\n%s", request.url, str(exc), stack_trace)
    return JSONResponse(
        status_code=500,
        content={
            "status": "failed",
            "type": "internal_server_error",
            "detail": "An unexpected error occurred. Please try again later.",
            "path": str(request.url),
        },
    )
