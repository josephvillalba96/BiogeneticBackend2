from fastapi import APIRouter
from app.routes import auth, users, bulls, races, sexes, roles, opus, inputs, outputs, produccion_embrionaria

router = APIRouter(
    prefix="/api",
    tags=["api"],
)

# Incluir todos los routers
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(bulls.router)
router.include_router(races.router)
router.include_router(sexes.router)
router.include_router(roles.router)
router.include_router(opus.router)
router.include_router(inputs.router)
router.include_router(outputs.router)
router.include_router(produccion_embrionaria.router)

@router.get("/status")
async def status():
    return {"status": "online"} 