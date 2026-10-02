# python -m uvicorn app.main:app --reload

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from fastapi.middleware.cors import CORSMiddleware

from app.routers import equipments, work_orders, auth, hospitals, users, diagnostic_logs
from app.config import settings

FRONTEND_ORIGIN = settings.frontend_origin
#os.environ.get("FRONTEND_ORIGIN" , "http://localhost:5173")

#set up the FastAPI application with a title, description, and version. 
# This metadata is used in the automatically generated OpenAPI documentation.
app = FastAPI(
    title="Hospital Equipment Command Center",
    description=(
        "Clinical equipment management API for Halcyon Health Systems' shared pool of "
        "portable medical devices. Tracks equipment inventories, manages biomed technician "
        "work order assignments, uploads service and diagnostic reports, and monitors "
        "real-time equipment health across all hospital and outpatient clinic locations."
    ),
    version="0.2.0", ##Day 9 change, bumped up from 0.1.0
)

#CORS Configuration
app.add_middleware(
    CORSMiddleware,
    #The endpoint for our frontent, currently provided by the vite dev server
    allow_origins=[FRONTEND_ORIGIN],
    #This allows us to pass an Authorization header (JWT)
    allow_credentials=True,
    #This allows all methods and headers through
    allow_methods=["*"],
    allow_headers=["*"]
)


#include the /equipments router in the FastAPI application. This means that all routes defined
# in the equipments router will be available under the /equipments path.
app.include_router(equipments.router)
app.include_router(work_orders.router)
app.include_router(auth.router)
app.include_router(hospitals.router)
app.include_router(users.router)
app.include_router(diagnostic_logs.router)

#A simple health check endpoint to verify that the API is running.
@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}

##Endpoint to check the version number
@app.get("/version", tags=["health"])
async def version() -> dict[str, str]:
    return {"version": app.version}


##BEGIN EXCEPTIONS

#This exception handles when our database constraint (specifically, our battery_level not being between 0 and 100)
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "A database constraint was violated (e.g. a duplicate value)"},
    )

#this is a catch-all exception handler so that ANY unexpected failur (bugs or unknown conditions) returns a
#constant JSON response
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error has occured."})