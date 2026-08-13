"""Data models for internal document representation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class SourceLocationType(str, Enum):
    """Enum representing the structural origin of a paragraph."""
    BODY = "body"
    TABLE = "table"
    HEADER = "header"
    FOOTER = "footer"


@dataclass
class SourceLocation:
    """Represents the exact location of a paragraph within the document structure."""
    location_type: SourceLocationType
    paragraph_index: int
    table_index: Optional[int] = None
    row_index: Optional[int] = None
    cell_index: Optional[int] = None
    header_kind: Optional[str] = None
    footer_kind: Optional[str] = None


@dataclass
class FormattingMetadata:
    """Formatting properties of a text run."""
    bold: bool = False
    italic: bool = False
    underline: bool = False
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None
    color_hex: Optional[str] = None
    style_name: Optional[str] = None


@dataclass
class RunModel:
    """Represents an individual text run (<w:r>) inside a paragraph."""
    run_index: int
    paragraph_index: int
    text: str
    start_offset: int
    end_offset: int  # Half-open interval [start_offset, end_offset)
    formatting: FormattingMetadata = field(default_factory=FormattingMetadata)


@dataclass
class ParagraphModel:
    """Represents a reconstructed paragraph composed of text runs."""
    paragraph_index: int
    reconstructed_text: str
    runs: List[RunModel] = field(default_factory=list)
    style_name: Optional[str] = None
    location: SourceLocation = field(
        default_factory=lambda: SourceLocation(
            location_type=SourceLocationType.BODY, paragraph_index=0
        )
    )


@dataclass
class HyperlinkModel:
    """Represents a hyperlink structure containing display text and relationship target."""
    relationship_id: str
    display_text: str
    target_uri: str
    relationship_type: str = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
    target_mode: Optional[str] = "External"
    location: Optional[SourceLocation] = None
    run_indices: List[int] = field(default_factory=list)


@dataclass
class RelationshipModel:
    """Represents a relationship entry from .rels XML structures."""
    relationship_id: str
    type: str
    target: str
    target_mode: Optional[str] = None


@dataclass
class TableCellModel:
    """Represents a cell inside a table row."""
    cell_index: int
    row_index: int
    table_index: int
    paragraphs: List[ParagraphModel] = field(default_factory=list)


@dataclass
class TableRowModel:
    """Represents a row inside a table."""
    row_index: int
    table_index: int
    cells: List[TableCellModel] = field(default_factory=list)


@dataclass
class TableModel:
    """Represents a table structure inside the document."""
    table_index: int
    rows: List[TableRowModel] = field(default_factory=list)


@dataclass
class HeaderFooterModel:
    """Represents a header or footer section."""
    kind: str  # e.g., 'primary_header', 'first_header', 'even_header', 'primary_footer', etc.
    paragraphs: List[ParagraphModel] = field(default_factory=list)


@dataclass
class DocumentModel:
    """Complete internal representation of an ingested DOCX document."""
    document_id: str
    file_name: Optional[str] = None
    paragraphs: List[ParagraphModel] = field(default_factory=list)
    tables: List[TableModel] = field(default_factory=list)
    headers: List[HeaderFooterModel] = field(default_factory=list)
    footers: List[HeaderFooterModel] = field(default_factory=list)
    hyperlinks: List[HyperlinkModel] = field(default_factory=list)
    relationships: Dict[str, RelationshipModel] = field(default_factory=dict)
    total_paragraphs: int = 0
    total_runs: int = 0
