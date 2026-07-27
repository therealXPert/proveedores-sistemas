from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    """Endpoint de salud usado por Cloud Run y para verificar el despliegue."""
    return {"status": "ok"}
