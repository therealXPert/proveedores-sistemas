from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import health, auth, imports, catalogs, providers, categories, areas, budgets, reports, audit

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restringir al dominio real del frontend en produccion
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(imports.router)
app.include_router(catalogs.router)
app.include_router(providers.router)
app.include_router(categories.router)
app.include_router(areas.router)
app.include_router(budgets.router)
app.include_router(reports.router)
app.include_router(audit.router)


@app.get("/")
def root():
    return {"app": settings.app_name, "environment": settings.environment}
