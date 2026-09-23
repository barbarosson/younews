"""User-defined RSS / HTML sources in Settings."""

from __future__ import annotations

import asyncio
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import SOCIAL_MODULE_ID
from core.i18n_manager import I18nManager
from core.rss_engine import refresh_one_rss
from core.source_probe import SourceProbeResult, probe_source
from database.db import Database, DuplicateSourceError, InvalidSourceUrlError, is_http_url
from database.models import Source


class SourcesTab(QWidget):
    def __init__(self, db: Database, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._i18n = i18n
        self.sources_changed = False

        self.hint = QLabel()
        self.hint.setWordWrap(True)

        self.table = QTableWidget(0, 6)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

        self.opml_import = QPushButton()
        self.opml_export = QPushButton()
        self.opml_import.setObjectName("ghostButton")
        self.opml_export.setObjectName("ghostButton")

        self.name_label = QLabel()
        self.url_label = QLabel()
        self.module_label = QLabel()
        self.topic_label = QLabel()
        self.kind_label = QLabel()
        self.css_label = QLabel()
        self.source_name = QLineEdit()
        self.source_url = QLineEdit()
        self.module_combo = QComboBox()
        self.topic_combo = QComboBox()
        self.kind_combo = QComboBox()
        self.css_edit = QLineEdit()
        self.add_btn = QPushButton()
        self.test_btn = QPushButton()
        self.test_btn.setObjectName("ghostButton")
        self.remove_btn = QPushButton()
        self.remove_btn.setObjectName("ghostButton")
        self.mute_btn = QPushButton()
        self.mute_btn.setObjectName("ghostButton")
        self.discover_btn = QPushButton()
        self.discover_btn.setObjectName("ghostButton")
        self.refresh_edit = QLineEdit()
        self.refresh_edit.setPlaceholderText("min")
        self.test_log_label = QLabel()
        self.test_log = QPlainTextEdit()
        self.test_log.setObjectName("sourceTestLog")
        self.test_log.setReadOnly(True)
        self.test_log.setMaximumHeight(150)

        form = QFormLayout()
        form.addRow(self.name_label, self.source_name)
        form.addRow(self.url_label, self.source_url)
        form.addRow(self.module_label, self.module_combo)
        form.addRow(self.topic_label, self.topic_combo)
        form.addRow(self.kind_label, self.kind_combo)
        form.addRow(self.css_label, self.css_edit)

        buttons = QHBoxLayout()
        buttons.addWidget(self.add_btn)
        buttons.addWidget(self.test_btn)
        buttons.addWidget(self.remove_btn)
        buttons.addWidget(self.mute_btn)
        buttons.addWidget(self.discover_btn)
        buttons.addWidget(self.refresh_edit)
        buttons.addWidget(self.opml_import)
        buttons.addWidget(self.opml_export)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(self.hint)
        layout.addWidget(self.table, 1)
        layout.addLayout(form)
        layout.addLayout(buttons)
        layout.addWidget(self.test_log_label)
        layout.addWidget(self.test_log)

        self.table.itemChanged.connect(self._on_item_changed)
        self.table.itemSelectionChanged.connect(self._on_selection)
        self.module_combo.currentIndexChanged.connect(self._reload_topics)
        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)
        self.add_btn.clicked.connect(self._add_source)
        self.test_btn.clicked.connect(self._test_form_source)
        self.remove_btn.clicked.connect(self._remove_source)
        self.mute_btn.clicked.connect(self._mute_source)
        self.discover_btn.clicked.connect(self._discover)
        self.opml_import.clicked.connect(self._import_opml)
        self.opml_export.clicked.connect(self._export_opml)
        self.source_url.returnPressed.connect(self._add_source)

        self.retranslate()
        self.reload()

    def _mark_changed(self) -> None:
        self.sources_changed = True
        dialog = self.window()
        if dialog is not None:
            setattr(dialog, "sources_changed", True)

    def retranslate(self) -> None:
        self.hint.setText(self._i18n.t("sources.hint"))
        self.table.setHorizontalHeaderLabels(
            [
                self._i18n.t("sources.active"),
                self._i18n.t("sources.name"),
                self._i18n.t("sources.url"),
                self._i18n.t("sources.module"),
                self._i18n.t("sources.kind"),
                self._i18n.t("sources.health"),
            ]
        )
        self.opml_import.setText(self._i18n.t("sources.opml_import"))
        self.opml_export.setText(self._i18n.t("sources.opml_export"))
        self.name_label.setText(self._i18n.t("sources.name"))
        self.url_label.setText(self._i18n.t("sources.url"))
        self.module_label.setText(self._i18n.t("sources.module"))
        self.topic_label.setText(self._i18n.t("sources.topic"))
        self.kind_label.setText(self._i18n.t("sources.kind"))
        self.css_label.setText(self._i18n.t("sources.css_selector"))
        self.source_name.setPlaceholderText(self._i18n.t("sources.name"))
        self.source_url.setPlaceholderText("https://")
        self.css_edit.setPlaceholderText(self._i18n.t("sources.css_hint"))
        self.add_btn.setText(self._i18n.t("sources.add"))
        self.test_btn.setText(self._i18n.t("sources.test"))
        self.remove_btn.setText(self._i18n.t("sources.remove"))
        self.mute_btn.setText(self._i18n.t("sources.mute"))
        self.discover_btn.setText(self._i18n.t("sources.discover"))
        self.test_log_label.setText(self._i18n.t("sources.test_log"))
        current_kind = self.kind_combo.currentData()
        self.kind_combo.blockSignals(True)
        self.kind_combo.clear()
        self.kind_combo.addItem(self._i18n.t("sources.rss"), "rss")
        self.kind_combo.addItem(self._i18n.t("sources.scraper"), "scraper")
        if current_kind:
            idx = self.kind_combo.findData(current_kind)
            if idx >= 0:
                self.kind_combo.setCurrentIndex(idx)
        self.kind_combo.blockSignals(False)
        self._fill_modules()
        self._reload_topics()
        self._on_kind_changed()
        self.reload()

    def reload(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        topics = {topic.id: topic for topic in self._db.list_topics()}
        for source in self._db.list_sources(active_only=False):
            if source.module_id == SOCIAL_MODULE_ID:
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            active = QTableWidgetItem()
            active.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )
            active.setCheckState(Qt.CheckState.Checked if source.is_active else Qt.CheckState.Unchecked)
            active.setData(Qt.ItemDataRole.UserRole, source.id)
            active.setData(Qt.ItemDataRole.UserRole + 1, int(source.user_added))
            name = QTableWidgetItem(source.name)
            url = QTableWidgetItem(source.url)
            url.setToolTip(source.url)
            module = QTableWidgetItem(self._module_label(source, topics))
            kind = QTableWidgetItem(
                self._i18n.t("sources.rss") if source.is_rss else self._i18n.t("sources.scraper")
            )
            if getattr(source, "last_ok", True):
                health = source.last_fetch_at or "OK"
            else:
                from core.app_extras import humanize_source_error

                health = humanize_source_error(
                    source.last_error or "",
                    self._i18n,
                ) or self._i18n.t("sources.unhealthy")
            status = QTableWidgetItem(str(health)[:120])
            status.setToolTip(str(health))
            self.table.setItem(row, 0, active)
            self.table.setItem(row, 1, name)
            self.table.setItem(row, 2, url)
            self.table.setItem(row, 3, module)
            self.table.setItem(row, 4, kind)
            self.table.setItem(row, 5, status)
        self.table.blockSignals(False)
        self._on_selection()

    def _module_label(self, source: Source, topics: dict) -> str:
        module_name = self._i18n.t(f"modules.{source.module_id}", source.module_id.title())
        topic = topics.get(source.topic_id or "")
        if topic is None:
            return module_name
        topic_name = self._i18n.t(topic.name_key, topic.id)
        return f"{module_name} · {topic_name}"

    def _fill_modules(self) -> None:
        current = self.module_combo.currentData()
        self.module_combo.blockSignals(True)
        self.module_combo.clear()
        for module in self._db.list_modules():
            if module.id == SOCIAL_MODULE_ID:
                continue
            self.module_combo.addItem(self._i18n.t(module.name_key, module.id.title()), module.id)
        if current:
            idx = self.module_combo.findData(current)
            if idx >= 0:
                self.module_combo.setCurrentIndex(idx)
        self.module_combo.blockSignals(False)

    def _reload_topics(self) -> None:
        module_id = self.module_combo.currentData()
        current = self.topic_combo.currentData()
        topics = self._db.list_topics(module_id=module_id) if module_id else []
        self.topic_combo.blockSignals(True)
        self.topic_combo.clear()
        self.topic_combo.addItem(self._i18n.t("sources.none"), None)
        indent: dict[str, int] = {}
        for topic in topics:
            depth = 0
            parent = topic.parent_id
            parents = {item.id: item for item in topics}
            while parent and parent in parents and depth < 6:
                depth += 1
                parent = parents[parent].parent_id
            indent[topic.id] = depth
            prefix = "  " * depth
            self.topic_combo.addItem(f"{prefix}{self._i18n.t(topic.name_key, topic.id)}", topic.id)
        if current:
            idx = self.topic_combo.findData(current)
            if idx >= 0:
                self.topic_combo.setCurrentIndex(idx)
        self.topic_combo.blockSignals(False)
        visible = bool(topics)
        self.topic_label.setVisible(visible)
        self.topic_combo.setVisible(visible)

    def _on_kind_changed(self) -> None:
        html = self.kind_combo.currentData() == "scraper"
        self.css_edit.setEnabled(html)

    def _selected_source(self) -> tuple[int | None, bool]:
        row = self.table.currentRow()
        if row < 0:
            return None, False
        item = self.table.item(row, 0)
        if item is None:
            return None, False
        source_id = item.data(Qt.ItemDataRole.UserRole)
        user_added = bool(item.data(Qt.ItemDataRole.UserRole + 1))
        return (int(source_id) if source_id is not None else None), user_added

    def _on_selection(self) -> None:
        source_id, user_added = self._selected_source()
        self.remove_btn.setEnabled(bool(source_id) and user_added)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() != 0:
            return
        source_id = item.data(Qt.ItemDataRole.UserRole)
        if source_id is None:
            return
        self._db.set_source_active(int(source_id), item.checkState() == Qt.CheckState.Checked)
        self._mark_changed()

    def _add_source(self) -> None:
        name = self.source_name.text().strip()
        url = self.source_url.text().strip()
        module_id = self.module_combo.currentData()
        if not name:
            QMessageBox.information(self, self._i18n.t("sources.title"), self._i18n.t("sources.name_required"))
            return
        if not module_id:
            return
        if not is_http_url(url):
            QMessageBox.warning(self, self._i18n.t("sources.title"), self._i18n.t("sources.invalid_url"))
            return
        is_rss = self.kind_combo.currentData() != "scraper"
        selector = self.css_edit.text().strip() or None
        if not is_rss and not selector:
            QMessageBox.information(self, self._i18n.t("sources.title"), self._i18n.t("sources.selector_required"))
            return
        topic_id = self.topic_combo.currentData() if self.topic_combo.isVisible() else None
        result = self._run_probe(url, is_rss=is_rss, selector=selector)
        try:
            source_id = self._db.add_user_source(
                name=name,
                url=url,
                module_id=str(module_id),
                is_rss=is_rss,
                css_selector=selector,
                topic_id=str(topic_id) if topic_id else None,
            )
        except DuplicateSourceError:
            QMessageBox.warning(self, self._i18n.t("sources.title"), self._i18n.t("sources.duplicate"))
            return
        except InvalidSourceUrlError:
            QMessageBox.warning(self, self._i18n.t("sources.title"), self._i18n.t("sources.invalid_url"))
            return
        self._mark_changed()
        self.source_name.clear()
        self.source_url.clear()
        self.css_edit.clear()
        source = self._db.get_source(source_id)
        pulled = 0
        if source and source.is_rss and result.ok:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                pulled = asyncio.run(refresh_one_rss(self._db, source))
                if pulled:
                    self._append_log([self._i18n.t("sources.test_stored").replace("{count}", str(pulled))])
            except Exception as exc:
                self._append_log([f"FAIL: {exc}"])
            finally:
                QApplication.restoreOverrideCursor()
        self.reload()
        self._notify_probe(name, result, saved=True, stored=pulled)

    def _test_form_source(self) -> None:
        url = self.source_url.text().strip()
        if not is_http_url(url):
            QMessageBox.warning(self, self._i18n.t("sources.title"), self._i18n.t("sources.invalid_url"))
            return
        is_rss = self.kind_combo.currentData() != "scraper"
        selector = self.css_edit.text().strip() or None
        if not is_rss and not selector:
            QMessageBox.information(self, self._i18n.t("sources.title"), self._i18n.t("sources.selector_required"))
            return
        result = self._run_probe(url, is_rss=is_rss, selector=selector)
        self._notify_probe(self.source_name.text().strip() or url, result, saved=False, stored=0)

    def _run_probe(self, url: str, *, is_rss: bool, selector: str | None) -> SourceProbeResult:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = probe_source(url, is_rss=is_rss, css_selector=selector)
        finally:
            QApplication.restoreOverrideCursor()
        self._append_log(result.lines)
        return result

    def _append_log(self, lines: list[str]) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        block = "\n".join(f"[{stamp}] {line}" for line in lines if str(line).strip())
        if not block:
            return
        self.test_log.appendPlainText(block)
        self.test_log.appendPlainText("")
        scrollbar = self.test_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _notify_probe(self, name: str, result: SourceProbeResult, *, saved: bool, stored: int) -> None:
        title = self._i18n.t("sources.test_title")
        if result.ok:
            message = (
                self._i18n.t("sources.test_ok")
                .replace("{name}", name)
                .replace("{count}", str(result.item_count))
                .replace("{ms}", str(result.elapsed_ms))
                .replace("{status}", str(result.status_code or ""))
            )
            if saved and stored:
                message += "\n" + self._i18n.t("sources.test_stored").replace("{count}", str(stored))
            elif saved:
                message += "\n" + self._i18n.t("sources.added")
            QMessageBox.information(self, title, message)
            return
        message = (
            self._i18n.t("sources.test_fail")
            .replace("{name}", name)
            .replace("{error}", result.error or self._i18n.t("sources.test_empty"))
        )
        if saved:
            message += "\n" + self._i18n.t("sources.added_but_failed")
        QMessageBox.warning(self, title, message)

    def _remove_source(self) -> None:
        source_id, user_added = self._selected_source()
        if source_id is None:
            QMessageBox.information(self, self._i18n.t("sources.title"), self._i18n.t("sources.select_first"))
            return
        if not user_added:
            QMessageBox.information(self, self._i18n.t("sources.title"), self._i18n.t("sources.cannot_delete_seed"))
            return
        if self._db.delete_user_source(source_id):
            self._mark_changed()
            self.reload()

    def _mute_source(self) -> None:
        source_id, _user = self._selected_source()
        if source_id is None:
            QMessageBox.information(self, self._i18n.t("sources.title"), self._i18n.t("sources.select_first"))
            return
        self._db.mute_source(source_id, 24)
        minutes = 0
        try:
            minutes = int(self.refresh_edit.text() or 0)
        except ValueError:
            minutes = 0
        if minutes:
            self._db.set_source_refresh_minutes(source_id, minutes)
        self._mark_changed()
        self.reload()

    def _discover(self) -> None:
        url = self.source_url.text().strip()
        if not is_http_url(url):
            QMessageBox.warning(self, self._i18n.t("sources.title"), self._i18n.t("sources.invalid_url"))
            return
        from core.app_extras import discover_rss

        found = discover_rss(url)
        if found:
            self.source_url.setText(found[0])
            self._append_log(found)
        else:
            QMessageBox.information(self, self._i18n.t("sources.title"), self._i18n.t("sources.discover_empty"))

    def _import_opml(self) -> None:
        from pathlib import Path

        from core.app_extras import parse_opml

        path, _filter = QFileDialog.getOpenFileName(self, self._i18n.t("sources.opml_import"), "", "OPML (*.opml *.xml)")
        if not path:
            return
        module_id = self.module_combo.currentData() or "economy_markets"
        added = 0
        for name, url in parse_opml(Path(path)):
            try:
                self._db.add_user_source(name=name, url=url, module_id=module_id, is_rss=True)
                added += 1
            except Exception:
                continue
        self._mark_changed()
        self.reload()
        QMessageBox.information(self, self._i18n.t("sources.title"), self._i18n.t("sources.opml_added").replace("{count}", str(added)))

    def _export_opml(self) -> None:
        from pathlib import Path

        from core.app_extras import export_opml

        path, _filter = QFileDialog.getSaveFileName(self, self._i18n.t("sources.opml_export"), "you-news.opml", "OPML (*.opml)")
        if not path:
            return
        export_opml(self._db.list_sources(active_only=False), Path(path))
