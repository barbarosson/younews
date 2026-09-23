from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from config import DEFAULT_THEME, SUPPORTED_LANGUAGES, UI_LANGUAGES, normalize_theme
from core.i18n_manager import I18nManager
from database.db import Database
from database.models import Module, Topic
from ui.branding import apply_mascot, apply_wordmark

ROLE_KIND = Qt.ItemDataRole.UserRole
ROLE_MODULE = Qt.ItemDataRole.UserRole + 1
ROLE_TOPIC = Qt.ItemDataRole.UserRole + 2
ROLE_LABEL = Qt.ItemDataRole.UserRole + 3
ROLE_ARCHIVE = Qt.ItemDataRole.UserRole + 4


class Sidebar(QFrame):
    module_selected = Signal(str)
    language_selected = Signal(str)
    theme_selected = Signal(str)
    settings_requested = Signal()
    help_requested = Signal()
    refresh_requested = Signal()
    chat_requested = Signal()

    def __init__(self, db: Database, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._db = db
        self._i18n = i18n
        self._modules: list[Module] = []
        self._counts: dict[str, int] = {}
        self._tree_expanded = True

        self.mascot = QLabel()
        self.mascot.setObjectName("brandMascot")
        self.mascot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.mascot.setScaledContents(False)
        self.logo = QLabel()
        self.logo.setObjectName("brandLogo")
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setScaledContents(False)
        self.brand = QLabel()
        self.brand.setObjectName("brand")
        self.brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand.setWordWrap(True)
        self.tagline = QLabel()
        self.tagline.setObjectName("brandTagline")
        self.tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tagline.setWordWrap(True)
        self.module_title = QLabel()
        self.module_title.setObjectName("paneTitle")
        self.expand_btn = QPushButton()
        self.expand_btn.setObjectName("ghostButton")
        self.expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.collapse_btn = QPushButton()
        self.collapse_btn.setObjectName("ghostButton")
        self.collapse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.module_tree = QTreeWidget()
        self.module_tree.setHeaderHidden(True)
        self.module_tree.setRootIsDecorated(True)
        self.module_tree.setAnimated(True)
        self.module_tree.setIndentation(16)
        self.module_tree.setObjectName("moduleTree")
        self.module_tree.setCursor(Qt.CursorShape.PointingHandCursor)
        self.module_tree.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        self.language_label = QLabel()
        self.language_combo = QComboBox()
        for code, name in UI_LANGUAGES.items():
            self.language_combo.addItem(name, code)
        self.theme_label = QLabel()
        self.theme_combo = QComboBox()
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("ghostButton")
        self.help_btn = QPushButton()
        self.help_btn.setObjectName("ghostButton")
        self.refresh_btn = QPushButton()
        self.chat_btn = QPushButton()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.addWidget(self.mascot)
        layout.addWidget(self.logo)
        layout.addWidget(self.brand)
        layout.addWidget(self.tagline)
        layout.addSpacing(8)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)
        title_row.addWidget(self.module_title, 1)
        title_row.addWidget(self.expand_btn)
        title_row.addWidget(self.collapse_btn)
        layout.addLayout(title_row)
        layout.addWidget(self.module_tree, 1)
        locale_row = QHBoxLayout()
        lang_col = QVBoxLayout()
        lang_col.setContentsMargins(0, 0, 0, 0)
        lang_col.addWidget(self.language_label)
        lang_col.addWidget(self.language_combo)
        theme_col = QVBoxLayout()
        theme_col.setContentsMargins(0, 0, 0, 0)
        theme_col.addWidget(self.theme_label)
        theme_col.addWidget(self.theme_combo)
        locale_row.addLayout(lang_col, 1)
        locale_row.addLayout(theme_col, 1)
        layout.addLayout(locale_row)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.chat_btn)
        layout.addWidget(self.help_btn)
        layout.addWidget(self.settings_btn)

        self.module_tree.currentItemChanged.connect(self._on_module)
        self.language_combo.currentIndexChanged.connect(self._on_language)
        self.theme_combo.currentIndexChanged.connect(self._on_theme)
        self.settings_btn.clicked.connect(self.settings_requested.emit)
        self.help_btn.clicked.connect(self.help_requested.emit)
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        self.chat_btn.clicked.connect(self.chat_requested.emit)
        self.expand_btn.clicked.connect(self.expand_tree)
        self.collapse_btn.clicked.connect(self.collapse_tree)
        expand_action = QAction(self)
        expand_action.setShortcut(QKeySequence("Ctrl+E"))
        expand_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        expand_action.triggered.connect(self.expand_tree)
        self.addAction(expand_action)
        collapse_action = QAction(self)
        collapse_action.setShortcut(QKeySequence("Ctrl+Shift+E"))
        collapse_action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        collapse_action.triggered.connect(self.collapse_tree)
        self.addAction(collapse_action)

        self.reload_modules()
        self.retranslate()
        self._refresh_logo()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._refresh_logo()

    def _refresh_logo(self) -> None:
        shown = apply_wordmark(self.logo, self.width() - 24)
        self.logo.setVisible(shown)
        self.brand.setVisible(not shown)
        mascot_ok = apply_mascot(self.mascot, min(120, max(88, self.width() - 48)))
        self.mascot.setVisible(mascot_ok)

    def reload_modules(self) -> None:
        current_module = self.current_module_id()
        current_topic = self.current_topic_id()
        current_archive = self.is_archive()
        self.module_tree.blockSignals(True)
        self.module_tree.clear()
        self._modules = self._db.list_modules(active_only=True)
        restore: QTreeWidgetItem | None = None
        all_label = self._i18n.t("app.all_news")
        all_item = QTreeWidgetItem([all_label])
        all_item.setData(0, ROLE_KIND, "all")
        all_item.setData(0, ROLE_MODULE, None)
        all_item.setData(0, ROLE_TOPIC, None)
        all_item.setData(0, ROLE_LABEL, all_label)
        self.module_tree.addTopLevelItem(all_item)
        if current_module is None and current_topic is None and not current_archive:
            restore = all_item
        module_branches: list[tuple[Module, dict[str | None, list[Topic]]]] = []
        for module in self._modules:
            label = self._i18n.t(module.name_key, module.id.title())
            root = QTreeWidgetItem([label])
            root.setData(0, ROLE_KIND, "module")
            root.setData(0, ROLE_MODULE, module.id)
            root.setData(0, ROLE_TOPIC, None)
            root.setData(0, ROLE_LABEL, label)
            self.module_tree.addTopLevelItem(root)
            if module.id == current_module and current_topic is None and not current_archive:
                restore = root
            topics = [topic for topic in self._db.list_topics(module.id, active_only=False) if topic.is_active]
            by_parent: dict[str | None, list[Topic]] = {}
            ids = {topic.id for topic in topics}
            for topic in topics:
                parent = topic.parent_id if topic.parent_id in ids else None
                if topic.parent_id and topic.parent_id not in ids:
                    continue
                by_parent.setdefault(parent, []).append(topic)
            nodes: dict[str, QTreeWidgetItem] = {}

            def add_children(parent_item: QTreeWidgetItem, parent_id: str | None, module_ref: Module = module) -> None:
                nonlocal restore
                for topic in by_parent.get(parent_id, []):
                    label = self._i18n.t(topic.name_key, topic.id)
                    child = QTreeWidgetItem([label])
                    child.setData(0, ROLE_KIND, "topic")
                    child.setData(0, ROLE_MODULE, module_ref.id)
                    child.setData(0, ROLE_TOPIC, topic.id)
                    child.setData(0, ROLE_LABEL, label)
                    parent_item.addChild(child)
                    nodes[topic.id] = child
                    if module_ref.id == current_module and topic.id == current_topic and not current_archive:
                        restore = child
                    add_children(child, topic.id, module_ref)

            add_children(root, None)
            self._apply_branch_state(root)
            module_branches.append((module, by_parent))
        archive_label = self._i18n.t("app.archive")
        archive_root = QTreeWidgetItem([archive_label])
        archive_root.setData(0, ROLE_KIND, "archive")
        archive_root.setData(0, ROLE_MODULE, None)
        archive_root.setData(0, ROLE_TOPIC, None)
        archive_root.setData(0, ROLE_LABEL, archive_label)
        archive_root.setData(0, ROLE_ARCHIVE, True)
        self.module_tree.addTopLevelItem(archive_root)
        if current_archive and current_module is None and current_topic is None:
            restore = archive_root
        for module, by_parent in module_branches:
            module_label = self._i18n.t(module.name_key, module.id.title())
            module_item = QTreeWidgetItem([module_label])
            module_item.setData(0, ROLE_KIND, "module")
            module_item.setData(0, ROLE_MODULE, module.id)
            module_item.setData(0, ROLE_TOPIC, None)
            module_item.setData(0, ROLE_LABEL, module_label)
            module_item.setData(0, ROLE_ARCHIVE, True)
            archive_root.addChild(module_item)
            if current_archive and module.id == current_module and current_topic is None:
                restore = module_item

            def add_archive_children(
                parent_item: QTreeWidgetItem,
                parent_id: str | None,
                module_ref: Module = module,
            ) -> None:
                nonlocal restore
                for topic in by_parent.get(parent_id, []):
                    child_label = self._i18n.t(topic.name_key, topic.id)
                    child = QTreeWidgetItem([child_label])
                    child.setData(0, ROLE_KIND, "topic")
                    child.setData(0, ROLE_MODULE, module_ref.id)
                    child.setData(0, ROLE_TOPIC, topic.id)
                    child.setData(0, ROLE_LABEL, child_label)
                    child.setData(0, ROLE_ARCHIVE, True)
                    parent_item.addChild(child)
                    if current_archive and module_ref.id == current_module and topic.id == current_topic:
                        restore = child
                    add_archive_children(child, topic.id, module_ref)

            add_archive_children(module_item, None)
        self._apply_branch_state(archive_root)
        if restore is None and self.module_tree.topLevelItemCount():
            restore = self.module_tree.topLevelItem(0)
        if restore is not None:
            self.module_tree.setCurrentItem(restore)
        self.module_tree.blockSignals(False)
        self._paint_counts()

    def expand_tree(self) -> None:
        self._tree_expanded = True
        self.module_tree.expandAll()

    def collapse_tree(self) -> None:
        self._tree_expanded = False
        self.module_tree.collapseAll()

    def _apply_branch_state(self, root: QTreeWidgetItem) -> None:
        if self._tree_expanded:
            root.setExpanded(True)
            for index in range(root.childCount()):
                child = root.child(index)
                if child is not None:
                    child.setExpanded(True)
                    for nested in range(child.childCount()):
                        leaf_parent = child.child(nested)
                        if leaf_parent is not None:
                            leaf_parent.setExpanded(True)
        else:
            root.setExpanded(False)

    def current_module_id(self) -> str | None:
        item = self.module_tree.currentItem()
        return item.data(0, ROLE_MODULE) if item else None

    def current_topic_id(self) -> str | None:
        item = self.module_tree.currentItem()
        if not item:
            return None
        return item.data(0, ROLE_TOPIC)

    def current_topic_ids(self) -> list[str] | None:
        topic_id = self.current_topic_id()
        if not topic_id:
            return None
        active = {topic.id for topic in self._db.list_topics(self.current_module_id(), active_only=True)}
        return [item for item in self._db.topic_subtree_ids(topic_id) if item in active]

    def is_archive(self) -> bool:
        item = self.module_tree.currentItem()
        while item is not None:
            if item.data(0, ROLE_KIND) == "archive" or bool(item.data(0, ROLE_ARCHIVE)):
                return True
            item = item.parent()
        return False

    def set_counts(self, counts: dict[str, int]) -> None:
        self._counts = dict(counts)
        self._paint_counts()

    def _paint_counts(self) -> None:
        def walk(item: QTreeWidgetItem) -> None:
            label = item.data(0, ROLE_LABEL) or item.text(0)
            kind = item.data(0, ROLE_KIND)
            topic_id = item.data(0, ROLE_TOPIC)
            module_id = item.data(0, ROLE_MODULE)
            archived = bool(item.data(0, ROLE_ARCHIVE)) or kind == "archive"
            if kind == "all":
                key = "all"
            elif kind == "archive" and not module_id:
                key = "archive"
            else:
                key = topic_id or module_id
                if archived and key:
                    key = f"archive:{key}"
            count = self._counts.get(key, 0) if key else 0
            item.setText(0, f"{label} ({count})")
            for index in range(item.childCount()):
                child = item.child(index)
                if child is not None:
                    walk(child)

        for index in range(self.module_tree.topLevelItemCount()):
            root = self.module_tree.topLevelItem(index)
            if root is not None:
                walk(root)

    def retranslate(self) -> None:
        self.brand.setText(self._i18n.t("app.brand", "You News"))
        self.tagline.setText(self._i18n.t("app.tagline", self._i18n.t("app.title")))
        self.logo.setToolTip(self._i18n.t("app.brand", "You News"))
        self.mascot.setToolTip(self._i18n.t("app.brand", "You News"))
        self.module_title.setText(self._i18n.t("app.modules"))
        self.expand_btn.setText(self._i18n.t("app.tree_expand"))
        self.collapse_btn.setText(self._i18n.t("app.tree_collapse"))
        self.expand_btn.setToolTip(self._i18n.t("app.tree_expand_tip"))
        self.collapse_btn.setToolTip(self._i18n.t("app.tree_collapse_tip"))
        self.language_label.setText(self._i18n.t("app.language"))
        self.theme_label.setText(self._i18n.t("app.theme"))
        self.settings_btn.setText(self._i18n.t("app.settings"))
        self.help_btn.setText(self._i18n.t("tutorial.title"))
        self.refresh_btn.setText(self._i18n.t("app.refresh"))
        self.chat_btn.setText(self._i18n.t("chat.title"))
        self.language_combo.blockSignals(True)
        if self.language_combo.findData(self._i18n.language) < 0 and self._i18n.language in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(SUPPORTED_LANGUAGES[self._i18n.language], self._i18n.language)
        index = self.language_combo.findData(self._i18n.language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        self.language_combo.blockSignals(False)
        current_theme = self.theme_combo.currentData()
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItem(self._i18n.t("app.theme_dark"), "dark")
        self.theme_combo.addItem(self._i18n.t("app.theme_light"), "light")
        theme_value = current_theme or self._db.get_setting("theme", DEFAULT_THEME)
        theme_index = self.theme_combo.findData(normalize_theme(theme_value))
        if theme_index >= 0:
            self.theme_combo.setCurrentIndex(theme_index)
        self.theme_combo.blockSignals(False)
        self.reload_modules()

    def sync_theme(self, theme: str | None) -> None:
        index = self.theme_combo.findData(normalize_theme(theme))
        if index < 0:
            return
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentIndex(index)
        self.theme_combo.blockSignals(False)

    def _on_module(self) -> None:
        self.module_selected.emit(self.current_module_id() or "")

    def _on_language(self) -> None:
        code = self.language_combo.currentData()
        if code:
            self.language_selected.emit(code)

    def _on_theme(self) -> None:
        theme = self.theme_combo.currentData()
        if theme:
            self.theme_selected.emit(theme)
