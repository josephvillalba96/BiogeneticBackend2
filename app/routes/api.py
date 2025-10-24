from fastapi import APIRouter
from app.routes import auth, users, bulls, races, sexes, roles, opus, inputs, outputs, produccion_embrionaria, calendar, transfer, informes, bull_performance, pagos, facturacion

router = APIRouter(
    prefix="/api",
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
router.include_router(calendar.router)
router.include_router(transfer.router)
router.include_router(informes.router)
router.include_router(bull_performance.router)
router.include_router(pagos.router)
router.include_router(facturacion.router)

@router.get("/status")
async def status():
    return {"status": "online"} 