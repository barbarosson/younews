from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QDate, QEvent, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyledItemDelegate,
    QStyle,
    QStyleOptionViewItem,
    QVBoxLayout,
)

from config import BRIEFING_HOURS_DEFAULT, BRIEFING_HOURS_OPTIONS, normalize_article_date_sort
from core.app_extras import relative_time, source_domain
from core.i18n_manager import I18nManager
from database.models import Article

ROLE_ID = Qt.ItemDataRole.UserRole
ROLE_TITLE = Qt.ItemDataRole.UserRole + 1
ROLE_SOURCE = Qt.ItemDataRole.UserRole + 2
ROLE_WHEN = Qt.ItemDataRole.UserRole + 3
ROLE_IMAGE = Qt.ItemDataRole.UserRole + 4
ROLE_READ = Qt.ItemDataRole.UserRole + 5
ROLE_MODULE = Qt.ItemDataRole.UserRole + 6
ROLE_EMOJI = Qt.ItemDataRole.UserRole + 7
ROLE_SAVED = Qt.ItemDataRole.UserRole + 8
ROLE_COMPACT = Qt.ItemDataRole.UserRole + 9
ROLE_LOW_DATA = Qt.ItemDataRole.UserRole + 10

MODULE_COLORS = {
    "economy_markets": QColor("#238636"),
    "crypto_web3": QColor("#f7931a"),
    "tech_mobility": QColor("#1f6feb"),
    "global_politics": QColor("#da3633"),
    "lifestyle_culture": QColor("#a371f7"),
    "sports_entertainment": QColor("#9e6a03"),
    "science_environment": QColor("#3fb950"),
    "social_media": QColor("#a78bfa"),
    "economy": QColor("#238636"),
    "tech": QColor("#1f6feb"),
    "sports": QColor("#9e6a03"),
    "politics": QColor("#da3633"),
}

_PIXMAP_CACHE: dict[str, QPixmap] = {}


class ArticleCardDelegate(QStyledItemDelegate):
    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:  # type: ignore[override]
        compact = bool(index.data(ROLE_COMPACT))
        return QSize(max(option.rect.width(), 280), 56 if compact else 96)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:  # type: ignore[override]
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = option.rect.adjusted(4, 3, -4, -3)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        is_read = bool(index.data(ROLE_READ))
        compact = bool(index.data(ROLE_COMPACT))
        low_data = bool(index.data(ROLE_LOW_DATA))
        pressed = bool(option.state & QStyle.StateFlag.State_Sunken)
        view = option.widget
        if view is not None:
            try:
                pressed = pressed or int(view.property("ynPressedRow") or -1) == index.row()
            except (TypeError, ValueError):
                pass
        if pressed:
            rect = rect.adjusted(2, 2, -2, -2)
        module_id = str(index.data(ROLE_MODULE) or "economy_markets")
        accent = MODULE_COLORS.get(module_id, QColor("#1f6feb"))

        if selected:
            fill = QColor("#163a66")
        elif hovered:
            fill = QColor("#1a2838")
        else:
            fill = QColor("#121a24")
        light = option.palette.window().color().lightness() > 140
        if light:
            fill = QColor("#c8e1ff") if selected else QColor("#eef4fa") if hovered else QColor("#ffffff")
        if pressed:
            fill = QColor("#0d2f57") if not light else QColor("#9ecbff")

        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), 10, 10)
        painter.fillPath(path, fill)
        if hovered or selected or pressed:
            ring = accent.lighter(130) if selected or pressed else QColor(accent.red(), accent.green(), accent.blue(), 140)
            painter.setPen(QPen(ring, 3 if selected or pressed else 1))
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 10, 10)
        if not is_read:
            painter.setPen(QPen(accent, 5 if selected else 3))
            painter.drawLine(rect.left() + 3, rect.top() + 10, rect.left() + 3, rect.bottom() - 10)

        thumb = QRect(rect.left() + 10, rect.top() + 10, 40 if compact else 112, 36 if compact else 76)
        image_path = index.data(ROLE_IMAGE)
        pixmap = None if low_data or compact else _load_thumb(image_path)
        if pixmap is not None:
            painter.setClipPath(_round_rect(thumb, 8))
            painter.drawPixmap(thumb, pixmap.scaled(thumb.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            painter.setClipping(False)
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent.darker(130) if fill.lightness() < 140 else accent.lighter(160))
            painter.drawRoundedRect(thumb, 8, 8)
            painter.setPen(QColor("#ffffff"))
            font = QFont(option.font)
            font.setBold(True)
            font.setPointSize(max(1, 11))
            painter.setFont(font)
            painter.drawText(thumb, Qt.AlignmentFlag.AlignCenter, (module_id[:2] or "N").upper())

        text_left = thumb.right() + 12
        text_right = rect.right() - 52
        title_rect = QRect(text_left, rect.top() + 10, max(40, text_right - text_left), 46)
        meta_rect = QRect(text_left, title_rect.bottom() + 2, max(40, text_right - text_left), 22)

        title_font = QFont(option.font)
        title_font.setPointSize(max(1, 11))
        title_font.setBold(not is_read)
        painter.setFont(title_font)
        painter.setPen(QColor("#f0f6fc") if fill.lightness() < 140 else QColor("#1f2328"))
        title = str(index.data(ROLE_TITLE) or "")
        emoji = str(index.data(ROLE_EMOJI) or "").strip()
        if emoji:
            title = f"{emoji}  {title}"
        painter.drawText(title_rect, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignTop, title)

        meta_font = QFont(option.font)
        meta_font.setPointSize(max(1, 9))
        painter.setFont(meta_font)
        painter.setPen(QColor("#8b949e") if fill.lightness() < 140 else QColor("#656d76"))
        source = str(index.data(ROLE_SOURCE) or "")
        when = str(index.data(ROLE_WHEN) or "")
        painter.drawText(meta_rect, Qt.AlignmentFlag.AlignVCenter, f"{source}  ·  {when}")

        hint_rect = QRect(rect.right() - 48, rect.top(), 42, rect.height())
        hint_font = QFont(option.font)
        hint_font.setPointSize(max(1, 9))
        hint_font.setBold(True)
        painter.setFont(hint_font)
        painter.setPen(accent)
        painter.drawText(hint_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "›")
        if selected:
            chip = QRect(rect.right() - 46, rect.bottom() - 26, 36, 18)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(accent)
            painter.drawRoundedRect(chip, 9, 9)
            painter.setPen(QColor("#ffffff"))
            mark_font = QFont(option.font)
            mark_font.setPointSize(max(1, 8))
            mark_font.setBold(True)
            painter.setFont(mark_font)
            painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, "✓")
        if bool(index.data(ROLE_SAVED)):
            painter.setPen(QColor("#e3b341"))
            painter.drawText(QRect(rect.right() - 48, rect.top() + 22, 42, 20), Qt.AlignmentFlag.AlignRight, "★")

        if not is_read:
            painter.setBrush(accent)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect.right() - 18, rect.top() + 12, 8, 8)

        painter.restore()


def _round_rect(rect: QRect, radius: int) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), radius, radius)
    return path


def _load_thumb(path_value: object) -> QPixmap | None:
    if not path_value:
        return None
    path = str(path_value)
    cached = _PIXMAP_CACHE.get(path)
    if cached is not None:
        return cached
    if not Path(path).is_file():
        return None
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None
    _PIXMAP_CACHE[path] = pixmap
    return pixmap


class ArticleList(QFrame):
    article_selected = Signal(int)
    economy_briefing_requested = Signal(int)
    module_briefing_requested = Signal(int)
    selected_briefing_requested = Signal(list)
    sort_changed = Signal(str)
    source_changed = Signal()
    hours_changed = Signal()
    follows_requested = Signal()
    mark_all_read_requested = Signal()

    def __init__(self, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._module_id = "economy_markets"
        self._heading = ""
        self._empty_override = None
        self._compact = False
        self._low_data = False
        self._relative = True
        self.breaking = QLabel()
        self.breaking.setObjectName("breakingBanner")
        self.breaking.setWordWrap(True)
        self.breaking.hide()
        self.search = QLineEdit()
        self.sort_combo = QComboBox()
        self.sort_combo.setMinimumWidth(108)
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(120)
        self.source_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.read_combo = QComboBox()
        self.read_combo.setMinimumWidth(88)
        self.mark_read_btn = QPushButton()
        self.mark_read_btn.setObjectName("ghostButton")
        self.last_update_label = QLabel()
        self.last_update_label.setObjectName("lastUpdateLabel")
        self.context_label = QLabel()
        self.context_label.setObjectName("tickerContextLabel")
        self.context_label.setWordWrap(True)
        self.context_label.hide()
        self.hours_combo = QComboBox()
        self.hours_combo.setMinimumWidth(72)
        self.custom_from = QDateEdit()
        self.custom_to = QDateEdit()
        self.custom_from.setCalendarPopup(True)
        self.custom_to.setCalendarPopup(True)
        self.custom_from.setMaximumWidth(118)
        self.custom_to.setMaximumWidth(118)
        self.custom_from.setDate(QDate.currentDate().addDays(-7))
        self.custom_to.setDate(QDate.currentDate())
        self.custom_from.hide()
        self.custom_to.hide()
        self.folder_combo = QComboBox()
        self.folder_combo.setMinimumWidth(96)
        self.economy_btn = QPushButton()
        self.module_btn = QPushButton()
        self.module_btn.setObjectName("ghostButton")
        self.selected_btn = QPushButton()
        self.selected_btn.setObjectName("ghostButton")
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("articleFeed")
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setUniformItemSizes(True)
        self.list_widget.setSpacing(2)
        self.list_widget.setMouseTracking(True)
        self.list_widget.setItemDelegate(ArticleCardDelegate(self.list_widget))
        self.list_widget.setCursor(Qt.CursorShape.PointingHandCursor)
        self.list_widget.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        self.list_widget.viewport().installEventFilter(self)
        self.list_widget.setProperty("ynPressedRow", -1)
        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.follows_btn = QPushButton()
        self.follows_btn.hide()
        self.follows_btn.clicked.connect(self.follows_requested.emit)

        actions = QHBoxLayout()
        actions.addWidget(self.hours_combo)
        actions.addWidget(self.custom_from)
        actions.addWidget(self.custom_to)
        actions.addWidget(self.folder_combo)
        actions.addWidget(self.economy_btn, 1)
        actions.addWidget(self.selected_btn, 1)

        search_row = QHBoxLayout()
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.source_combo)
        search_row.addWidget(self.read_combo)
        search_row.addWidget(self.mark_read_btn)
        search_row.addWidget(self.sort_combo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.breaking)
        layout.addLayout(search_row)
        layout.addWidget(self.last_update_label)
        layout.addWidget(self.context_label)
        layout.addLayout(actions)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.follows_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        self.list_widget.currentItemChanged.connect(self._on_select)
        self.economy_btn.clicked.connect(lambda: self.economy_briefing_requested.emit(self.hours()))
        self.selected_btn.clicked.connect(self._emit_selected)
        self.hours_combo.currentIndexChanged.connect(self._on_hours_changed)
        self.custom_from.dateChanged.connect(self.hours_changed.emit)
        self.custom_to.dateChanged.connect(self.hours_changed.emit)
        self.folder_combo.currentIndexChanged.connect(self._on_source_changed)
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        self.read_combo.currentIndexChanged.connect(self._on_source_changed)
        self.mark_read_btn.clicked.connect(self.mark_all_read_requested.emit)
        self.retranslate()

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.list_widget.viewport():
            kind = event.type()
            if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                item = self.list_widget.itemAt(event.position().toPoint())
                row = self.list_widget.row(item) if item is not None else -1
                self.list_widget.setProperty("ynPressedRow", row)
                self.list_widget.viewport().update()
            elif kind in {QEvent.Type.MouseButtonRelease, QEvent.Type.Leave}:
                if int(self.list_widget.property("ynPressedRow") or -1) != -1:
                    self.list_widget.setProperty("ynPressedRow", -1)
                    self.list_widget.viewport().update()
        return super().eventFilter(watched, event)

    def date_sort(self) -> str:
        return normalize_article_date_sort(self.sort_combo.currentData())

    def set_date_sort(self, value: str | None) -> None:
        order = normalize_article_date_sort(value)
        index = self.sort_combo.findData(order)
        if index >= 0:
            self.sort_combo.blockSignals(True)
            self.sort_combo.setCurrentIndex(index)
            self.sort_combo.blockSignals(False)

    def _on_sort_changed(self) -> None:
        self.sort_changed.emit(self.date_sort())

    def unread_only(self) -> bool:
        return self.read_combo.currentData() == "unread"

    def source_id(self) -> int | None:
        value = self.source_combo.currentData()
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def set_source_options(self, sources: list[tuple[int, str]]) -> None:
        current = self.source_id()
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        self.source_combo.addItem(self._i18n.t("app.filter_source_all"), None)
        for source_id, name in sources:
            self.source_combo.addItem(name, source_id)
        if current is not None:
            index = self.source_combo.findData(current)
            if index >= 0:
                self.source_combo.setCurrentIndex(index)
        self.source_combo.blockSignals(False)
        self.source_combo.setToolTip(self._i18n.t("app.filter_source"))

    def _on_source_changed(self) -> None:
        self.source_changed.emit()

    def set_display_options(self, *, compact: bool, low_data: bool, relative: bool) -> None:
        self._compact = compact
        self._low_data = low_data
        self._relative = relative

    def set_breaking(self, text: str = "") -> None:
        if text:
            self.breaking.setText(text)
            self.breaking.show()
        else:
            self.breaking.hide()
            self.breaking.clear()

    def folder(self) -> str | None:
        value = self.folder_combo.currentData()
        return str(value) if value else None

    def set_folder_options(self, folders: list[str]) -> None:
        current = self.folder()
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        self.folder_combo.addItem(self._i18n.t("app.folder_all"), "")
        for name in folders:
            self.folder_combo.addItem(name, name)
        if current:
            idx = self.folder_combo.findData(current)
            if idx >= 0:
                self.folder_combo.setCurrentIndex(idx)
        self.folder_combo.blockSignals(False)

    def hours(self) -> int:
        data = self.hours_combo.currentData()
        if data == "custom":
            start = datetime(self.custom_from.date().year(), self.custom_from.date().month(), self.custom_from.date().day())
            end = datetime(self.custom_to.date().year(), self.custom_to.date().month(), self.custom_to.date().day())
            delta = max(1, int((end - start).total_seconds() // 3600) or 24)
            return min(delta, 24 * 365)
        return int(data or BRIEFING_HOURS_DEFAULT)

    def _on_hours_changed(self) -> None:
        custom = self.hours_combo.currentData() == "custom"
        self.custom_from.setVisible(custom)
        self.custom_to.setVisible(custom)
        self.retranslate()
        self.hours_changed.emit()

    def set_module(self, module_id: str | None, heading: str | None = None) -> None:
        self._module_id = module_id or ""
        if heading is not None:
            self._heading = heading
        self.retranslate()

    def selected_ids(self) -> list[int]:
        ids: list[int] = []
        for item in self.list_widget.selectedItems():
            value = item.data(ROLE_ID)
            if value is not None:
                ids.append(int(value))
        return ids

    def set_busy(self, busy: bool) -> None:
        self.economy_btn.setEnabled(not busy)
        self.selected_btn.setEnabled(not busy)
        self.hours_combo.setEnabled(not busy)
        if busy:
            self.economy_btn.setText(self._i18n.t("ai.summarizing"))
        else:
            self.retranslate()

    def retranslate(self) -> None:
        self.search.setPlaceholderText(self._i18n.t("app.search_placeholder"))
        current_sort = self.sort_combo.currentData()
        self.sort_combo.blockSignals(True)
        self.sort_combo.clear()
        self.sort_combo.addItem(self._i18n.t("app.sort_newest"), "newest")
        self.sort_combo.addItem(self._i18n.t("app.sort_oldest"), "oldest")
        if current_sort:
            idx = self.sort_combo.findData(current_sort)
            if idx >= 0:
                self.sort_combo.setCurrentIndex(idx)
        self.sort_combo.blockSignals(False)
        self.sort_combo.setToolTip(self._i18n.t("app.sort_date"))
        current_source = self.source_combo.currentData()
        if self.source_combo.count() == 0:
            self.source_combo.blockSignals(True)
            self.source_combo.addItem(self._i18n.t("app.filter_source_all"), None)
            self.source_combo.blockSignals(False)
        else:
            self.source_combo.blockSignals(True)
            self.source_combo.setItemText(0, self._i18n.t("app.filter_source_all"))
            if current_source is not None:
                idx = self.source_combo.findData(current_source)
                if idx >= 0:
                    self.source_combo.setCurrentIndex(idx)
            self.source_combo.blockSignals(False)
        self.source_combo.setToolTip(self._i18n.t("app.filter_source"))
        current_read = self.read_combo.currentData()
        self.read_combo.blockSignals(True)
        self.read_combo.clear()
        self.read_combo.addItem(self._i18n.t("app.filter_read_all"), "all")
        self.read_combo.addItem(self._i18n.t("app.unread"), "unread")
        idx = self.read_combo.findData(current_read or "all")
        if idx >= 0:
            self.read_combo.setCurrentIndex(idx)
        self.read_combo.blockSignals(False)
        self.mark_read_btn.setText(self._i18n.t("app.mark_all_read"))
        self._fill_hours_combo()
        self.empty_label.setText(self._empty_override or self._i18n.t("app.empty_feed"))
        self.follows_btn.setText(self._i18n.t("social.add"))
        hours = self.hours()
        heading = self._heading or (
            self._i18n.t("app.all_news")
            if not self._module_id
            else self._i18n.t(f"modules.{self._module_id}", self._module_id.title())
        )
        self.economy_btn.setText(
            self._i18n.t("ai.brief_module")
            .replace("{hours}", str(hours))
            .replace("{module}", heading)
        )
        self.selected_btn.setText(self._i18n.t("ai.brief_selected"))
        self.module_btn.setVisible(False)
        self.hours_combo.setToolTip(self._i18n.t("ai.hours_hint"))

    def _fill_hours_combo(self) -> None:
        current = self.hours_combo.currentData()
        self.hours_combo.blockSignals(True)
        self.hours_combo.clear()
        for hours in BRIEFING_HOURS_OPTIONS:
            label = self._i18n.t("ai.hours_option").replace("{hours}", str(hours))
            self.hours_combo.addItem(label, hours)
        self.hours_combo.addItem(self._i18n.t("app.custom_range"), "custom")
        target = current if current in BRIEFING_HOURS_OPTIONS or current == "custom" else BRIEFING_HOURS_DEFAULT
        index = self.hours_combo.findData(target)
        if index >= 0:
            self.hours_combo.setCurrentIndex(index)
        self.hours_combo.blockSignals(False)

    def current_article_id(self) -> int | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        value = item.data(ROLE_ID)
        return int(value) if value is not None else None

    def set_last_update_text(self, text: str) -> None:
        self.last_update_label.setText(text)

    def set_context_banner(self, text: str = "") -> None:
        if text:
            self.context_label.setText(text)
            self.context_label.show()
        else:
            self.context_label.hide()
            self.context_label.clear()

    def set_articles(self, articles: list[Article], empty_text: str | None = None) -> None:
        current_id = None
        if self.list_widget.currentItem():
            current_id = self.list_widget.currentItem().data(ROLE_ID)
        self.list_widget.blockSignals(True)
        self.list_widget.setUpdatesEnabled(False)
        self.list_widget.clear()
        self.empty_label.setVisible(not articles)
        self.list_widget.setVisible(bool(articles))
        self.follows_btn.setVisible(not articles and self._module_id == "social_media")
        if articles:
            self._empty_override = None
        elif empty_text:
            self._empty_override = empty_text
        self.empty_label.setText(self._empty_override or self._i18n.t("app.empty_feed"))
        restore_row = 0
        for index, article in enumerate(articles):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 56 if self._compact else 96))
            _bind_article_item(item, article, self._i18n, compact=self._compact, low_data=self._low_data, relative=self._relative)
            self.list_widget.addItem(item)
            if article.id == current_id:
                restore_row = index
        if articles:
            self.list_widget.setCurrentRow(restore_row)
        self.list_widget.blockSignals(False)
        self.list_widget.setUpdatesEnabled(True)
        if articles:
            self._on_select()

    def apply_thumbnail(self, article_id: int, image_path: str) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item and item.data(ROLE_ID) == article_id:
                item.setData(ROLE_IMAGE, image_path)
                break
        self.list_widget.viewport().update()

    def mark_item_read(self, article_id: int) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item and item.data(ROLE_ID) == article_id:
                item.setData(ROLE_READ, True)
                break
        self.list_widget.viewport().update()

    def _emit_selected(self) -> None:
        self.selected_briefing_requested.emit(self.selected_ids())

    def _on_select(self) -> None:
        item = self.list_widget.currentItem()
        if item:
            self.article_selected.emit(int(item.data(ROLE_ID)))


def _bind_article_item(
    item: QListWidgetItem,
    article: Article,
    i18n: I18nManager,
    *,
    compact: bool = False,
    low_data: bool = False,
    relative: bool = True,
) -> None:
    source = article.source_name or i18n.t("app.source")
    domain = source_domain(article.link or "")
    if domain:
        source = f"{source} ({domain})"
    if relative and article.pub_date:
        when = relative_time(article.pub_date)
    else:
        when = article.pub_date.strftime("%Y-%m-%d %H:%M") if article.pub_date else ""
    item.setData(ROLE_ID, article.id)
    item.setData(ROLE_TITLE, article.title)
    item.setData(ROLE_SOURCE, source)
    item.setData(ROLE_WHEN, when)
    item.setData(ROLE_IMAGE, article.image_path)
    item.setData(ROLE_READ, article.is_read)
    item.setData(ROLE_MODULE, article.module_id or "")
    item.setData(ROLE_EMOJI, article.emoji or "")
    item.setData(ROLE_SAVED, bool(article.is_saved))
    item.setData(ROLE_COMPACT, compact)
    item.setData(ROLE_LOW_DATA, low_data)
    item.setToolTip(article.title)
