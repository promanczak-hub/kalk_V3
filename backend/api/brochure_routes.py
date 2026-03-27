"""
Brochure PDF generation endpoint.
Uses Playwright (Chromium headless) to render HTML template → PDF blob.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Brochure"])

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_jinja_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True)


class EquipmentCategory(BaseModel):
    category_name: str
    items: list[str]


class BrochureRequest(BaseModel):
    brand: str
    model: str
    trim_level: str | None = None
    engine_description: str | None = None
    power_hp: int | None = None
    body_type: str | None = None
    transmission: str | None = None
    drive_type: str | None = None
    hero_image_url: str | None = None
    equipment_categories: list[EquipmentCategory] = []
    notes: str | None = None


def _render_html(data: BrochureRequest) -> str:
    template = _jinja_env.get_template("brochure_a4.html")
    return template.render(
        brand=data.brand,
        model=data.model,
        trim_level=data.trim_level,
        engine_description=data.engine_description,
        power_hp=data.power_hp,
        body_type=data.body_type,
        transmission=data.transmission,
        hero_image_url=data.hero_image_url,
        equipment_categories=data.equipment_categories,
        notes=data.notes or "",
    )


async def _html_to_pdf(html: str) -> bytes:
    """Render HTML string to PDF bytes using Playwright Chromium."""
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail="Playwright not installed. Run: playwright install chromium",
        ) from exc

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        pdf_bytes: bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        await browser.close()
    return pdf_bytes


@router.post("/brochure/preview-html", response_class=Response)
def brochure_preview_html(data: BrochureRequest) -> Response:
    """Return rendered HTML for iframe preview (no PDF overhead)."""
    html = _render_html(data)
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.post("/brochure/generate-pdf")
async def brochure_generate_pdf(data: BrochureRequest) -> Response:
    """Render HTML template and convert to PDF via Playwright."""
    logger.info("Generating brochure PDF for %s %s", data.brand, data.model)
    html = _render_html(data)
    try:
        pdf_bytes = await _html_to_pdf(html)
    except Exception as exc:
        logger.error("PDF generation failed: %s", exc)
        raise HTTPException(
            status_code=500, detail=f"PDF generation failed: {exc}"
        ) from exc

    filename = f"Broszura_{data.brand}_{data.model}.pdf".replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
