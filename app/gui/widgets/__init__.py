"""UI Widgets for the modern document workspace."""

from app.gui.widgets.confidence_badge import ConfidenceBadge, StatusBadge
from app.gui.widgets.confirm_dialog import ConfirmOperationDialog
from app.gui.widgets.document_inspector import DocumentInspectorWidget
from app.gui.widgets.empty_state import EmptyStateWidget
from app.gui.widgets.folder_drop_zone import FolderDropZone
from app.gui.widgets.search_bar import SearchBar
from app.gui.widgets.theme import Theme

__all__ = [
    "ConfidenceBadge",
    "ConfirmOperationDialog",
    "DocumentInspectorWidget",
    "EmptyStateWidget",
    "FolderDropZone",
    "SearchBar",
    "StatusBadge",
    "Theme",
]
