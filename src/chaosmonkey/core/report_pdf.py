"""PDF report generator for chaos experiments using WeasyPrint."""
import io
from typing import Optional
from pathlib import Path

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


def generate_pdf_from_html(html_content: str, output_path: Optional[Path] = None) -> bytes:
    """Generate a PDF report from HTML content.
    
    Args:
        html_content: HTML string content to convert to PDF
        output_path: Optional path to save the PDF file
        
    Returns:
        bytes: PDF content as bytes
        
    Raises:
        ImportError: If WeasyPrint is not installed
        Exception: If PDF generation fails
    """
    if not WEASYPRINT_AVAILABLE:
        raise ImportError(
            "WeasyPrint is not installed. Please install it with: pip install weasyprint"
        )
    
    try:
        # Create HTML object from string
        html = HTML(string=html_content)
        
        # Additional CSS for better PDF rendering
        pdf_css = CSS(string='''
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-size: 10pt;
            }
            .no-print {
                display: none;
            }
        ''')
        
        # Generate PDF
        if output_path:
            # Write to file
            html.write_pdf(output_path, stylesheets=[pdf_css])
            return output_path.read_bytes()
        else:
            # Return as bytes
            pdf_bytes = html.write_pdf(stylesheets=[pdf_css])
            return pdf_bytes
            
    except Exception as e:
        raise Exception(f"Failed to generate PDF: {str(e)}")


def is_pdf_generation_available() -> bool:
    """Check if PDF generation is available (WeasyPrint installed)."""
    return WEASYPRINT_AVAILABLE
