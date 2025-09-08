# Modelos de datos para la base de datos 

# Importar todos los modelos aquí para resolver las dependencias circulares
from app.models.base_model import Base, BaseModel
from app.models.user import User, Role, DocumentType
from app.models.bull import Bull, Race, Sex
from app.models.opus import Opus, ProduccionEmbrionaria, Transferencia, ReportTransfer
from app.models.relationships import setup_relationships
from app.models.calendar import CalendarTask, CalendarTaskType, CalendarTemplate, CalendarTemplateTask

# Configurar las relaciones entre modelos
setup_relationships()

# Exportar todos los modelos
__all__ = [
    'Base',
    'BaseModel',
    'User',
    'Role',
    'DocumentType',
    'Bull',
    'Race',
    'Sex',
    'Opus',
    'CalendarTask',
    'CalendarTaskType',
    'CalendarTemplate',
    'CalendarTemplateTask'
]

# Función para verificar si los modelos están correctamente mapeados
def verify_all_models():
    return {
        "User": User.__table__,
        "Role": Role.__table__,
        "Bull": Bull.__table__,
        "Race": Race.__table__,
        "Sex": Sex.__table__,
        "Opus": Opus.__table__,
        "CalendarTask": CalendarTask.__table__,
        "CalendarTaskType": CalendarTaskType.__table__,
        "CalendarTemplate": CalendarTemplate.__table__,
        "CalendarTemplateTask": CalendarTemplateTask.__table__
    } 