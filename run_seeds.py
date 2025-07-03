import logging
from seed_roles import seed_roles
from seed_bull_data import seed_races, seed_sexes
from seed_users import seed_admin_user, seed_regular_user, seed_client_user

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Función principal para ejecutar todas las seeds"""
    try:
        logger.info("=== Iniciando proceso de sembrado de datos ===")

        # 1. Sembrar roles (necesario para los usuarios)
        logger.info("--- Sembrando roles ---")
        seed_roles()
        logger.info("✓ Roles sembrados correctamente")

        # 2. Sembrar datos de toros
        logger.info("--- Sembrando datos de razas y sexos ---")
        seed_races()
        seed_sexes()
        logger.info("✓ Datos de razas y sexos sembrados correctamente")

        # 3. Sembrar usuarios
        logger.info("--- Sembrando usuarios ---")
        seed_admin_user()
        seed_regular_user()
        seed_client_user()
        logger.info("✓ Usuarios sembrados correctamente")

        logger.info("=== Proceso de sembrado completado exitosamente ===")
    except Exception as e:
        logger.error("¡Error durante el proceso de sembrado!")
        logger.error(f"Detalles del error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    main() 