from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.contracts.router import router as contracts_router
from app.api.v1.invoices.router import router as invoices_router
from app.api.v1.compliance.router import router as compliance_router
from app.api.v1.documents.router import router as documents_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(contracts_router)
api_router.include_router(invoices_router)
api_router.include_router(compliance_router)
api_router.include_router(documents_router)