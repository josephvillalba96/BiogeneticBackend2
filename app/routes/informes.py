from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io

from app.database.base import get_db
from app.services.auth_service import get_current_user_from_token
from app.models.user import User
from app.services.informes_service import render_produccion_html
from app.models.opus import ProduccionEmbrionaria
from app.services import role_service

# Playwright
from playwright.sync_api import sync_playwright, Error as PlaywrightError
import logging
import traceback
import re


router = APIRouter(
    prefix="/informes",
    tags=["informes"],
    responses={404: {"description": "No encontrado"}},
)

logger = logging.getLogger(__name__)


def _sanitize_html_for_pdf(html: str) -> str:
    """Quita scripts externos problemáticos pero mantiene Chart.js para gráficos.
    Mantiene el resto del contenido para impresión.
    """
    # Eliminar scripts externos problemáticos pero mantener Chart.js
    html = re.sub(r"<script[^>]+src=\"https://cdnjs\.cloudflare\.com/ajax/libs/html2pdf\.js[^\"]*\"[^>]*></script>", "", html, flags=re.IGNORECASE)
    return html


def html_to_pdf_bytes(html: str) -> bytes:
    """Renderiza HTML a PDF usando Playwright (Chromium headless)."""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError:
            # Fallback a navegadores del sistema si no se descargó Chromium de Playwright
            try:
                browser = p.chromium.launch(channel="msedge")
            except PlaywrightError:
                browser = p.chromium.launch(channel="chrome")
        page = browser.new_page()
        # Saneamos HTML para evitar dependencias externas en generación de PDF
        html_sanitized = _sanitize_html_for_pdf(html)
        # Cargar HTML y esperar a que termine la actividad de red
        page.set_content(html_sanitized, wait_until="networkidle", timeout=120000)
        
        # Esperar a que Chart.js se cargue y renderice el gráfico
        try:
            # Esperar a que el canvas del gráfico esté presente y tenga contenido
            page.wait_for_selector("canvas", timeout=10000)
            # Dar tiempo adicional para que Chart.js termine de renderizar
            page.wait_for_timeout(3000)  # 3 segundos adicionales
        except Exception as e:
            logger.warning(f"Timeout esperando gráfico: {e}")
        
        # Emular media 'print' para respetar estilos @media print
        page.emulate_media(media="print")
        # Configurar PDF con tamaño carta y manejo de saltos
        pdf_bytes = page.pdf(
            format="Letter",
            print_background=True,
            margin={"top": "0.5in", "right": "0.5in", "bottom": "0.5in", "left": "0.5in"},
            prefer_css_page_size=True,
        )
        browser.close()
        return pdf_bytes


@router.get("/produccion/{produccion_id}/pdf")
def generar_informe_produccion_pdf(
    produccion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """
    Genera un PDF de informe de Producción Embrionaria usando la plantilla embrionary_production.html.
    """
    try:
        # Autorización: admin puede ver cualquiera; cliente solo su propia producción
        produccion = (
            db.query(ProduccionEmbrionaria)
            .filter(ProduccionEmbrionaria.id == produccion_id)
            .first()
        )
        if not produccion:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producción no encontrada")
        # Admin puede ver cualquier producción; cliente solo la suya
        es_admin = getattr(current_user, "is_admin", False) or role_service.is_admin(current_user)
        if (not es_admin) and produccion.cliente_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para este recurso")

        html = render_produccion_html(db, produccion_id, current_user)
        pdf_bytes = html_to_pdf_bytes(html)

        filename = f"informe_produccion_{produccion_id}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={filename}",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error generando PDF para produccion_id={produccion_id}: {tb}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error generando PDF: {e}\n{tb}")


@router.get("/produccion/{produccion_id}/html")
def previsualizar_informe_produccion_html(
    produccion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    """Devuelve el HTML renderizado para depuración sin PDF."""
    # Autorización similar
    produccion = (
        db.query(ProduccionEmbrionaria)
        .filter(ProduccionEmbrionaria.id == produccion_id)
        .first()
    )
    if not produccion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producción no encontrada")
    es_admin = getattr(current_user, "is_admin", False) or role_service.is_admin(current_user)
    if (not es_admin) and produccion.cliente_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para este recurso")

    try:
        html = render_produccion_html(db, produccion_id, current_user)
        return StreamingResponse(io.BytesIO(html.encode("utf-8")), media_type="text/html; charset=utf-8")
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"Error renderizando HTML para produccion_id={produccion_id}: {tb}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error renderizando HTML: {e}\n{tb}")


