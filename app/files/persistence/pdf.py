from io import BytesIO

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

from app.files.domain.errors import InvalidPdf
from app.files.domain.ports import PdfMerger


class PypdfMerger(PdfMerger):
    """Adaptador sobre pypdf.

    Es la unica parte del modulo que conoce la libreria: cambiarla no obliga a tocar el dominio.
    """

    def merge(self, documents: list[bytes]) -> bytes:
        writer = PdfWriter()
        for position, document in enumerate(documents, start=1):
            try:
                for page in PdfReader(BytesIO(document)).pages:
                    writer.add_page(page)
            except (PdfReadError, ValueError):
                raise InvalidPdf(position) from None

        buffer = BytesIO()
        writer.write(buffer)
        return buffer.getvalue()
