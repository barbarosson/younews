"""Follow YouTube, Substack, and Bluesky accounts via public RSS."""

from __future__ import annotations

from PySide6.QtCore import Qt
from datetime import datetime

from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
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

from config import SOCIAL_FOLLOW_LIMIT, SOCIAL_MODULE_ID
from core.i18n_manager import I18nManager
from core.social_resolve import PLATFORMS, SUPPORTED, SocialResolveError, TOPIC_IDS, detect_platform, resolve_follow
from core.source_probe import probe_source
from database.db import Database, DuplicateSourceError
from database.models import Source


class SocialFollowsTab(QWidget):
    def __init__(self, db: Database, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._i18n = i18n
        self.sources_changed = False

        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.limit_label = QLabel()
        self.platform = QComboBox()
        self.handle = QLineEdit()
        self.add_btn = QPushButton()
        self.test_btn = QPushButton()
        self.test_btn.setObjectName("ghostButton")
        self.remove_btn = QPushButton()
        self.remove_btn.setObjectName("ghostButton")
        self.test_log_label = QLabel()
        self.test_log = QPlainTextEdit()
        self.test_log.setObjectName("sourceTestLog")
        self.test_log.setReadOnly(True)
        self.test_log.setMaximumHeight(160)
        self.table = QTableWidget(0, 3)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        row = QHBoxLayout()
        row.addWidget(self.platform)
        row.addWidget(self.handle, 1)
        row.addWidget(self.test_btn)
        row.addWidget(self.add_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.hint)
        layout.addWidget(self.limit_label)
        layout.addLayout(row)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.remove_btn, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.test_log_label)
        layout.addWidget(self.test_log)

        self.add_btn.clicked.connect(self._add)
        self.test_btn.clicked.connect(self._test)
        self.remove_btn.clicked.connect(self._remove)
        self.handle.returnPressed.connect(self._add)
        self.table.itemSelectionChanged.connect(self._sync_remove)
        self.platform.currentIndexChanged.connect(self._on_platform)

        self.retranslate()
        self.reload()

    def retranslate(self) -> None:
        self.hint.setText(self._i18n.t("social.hint"))
        self.handle.setPlaceholderText(self._i18n.t("social.handle_placeholder"))
        self.add_btn.setText(self._i18n.t("social.add"))
        self.test_btn.setText(self._i18n.t("social.test"))
        self.test_log_label.setText(self._i18n.t("social.test_log"))
        self.remove_btn.setText(self._i18n.t("social.remove"))
        self.table.setHorizontalHeaderLabels(
            [
                self._i18n.t("social.col_platform"),
                self._i18n.t("social.col_name"),
                self._i18n.t("social.col_feed"),
            ]
        )
        current = self.platform.currentData()
        self.platform.blockSignals(True)
        self.platform.clear()
        for key in PLATFORMS:
            self.platform.addItem(self._i18n.t(f"social.platform.{key}", key.title()), key)
        if current:
            idx = self.platform.findData(current)
            if idx >= 0:
                self.platform.setCurrentIndex(idx)
        self.platform.blockSignals(False)
        self._refresh_limit()
        self._on_platform()
        self._sync_remove()

    def reload(self) -> None:
        self.table.setRowCount(0)
        follows = [
            source
            for source in self._db.list_sources(active_only=False)
            if source.module_id == SOCIAL_MODULE_ID and source.user_added
        ]
        for source in follows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            platform = _platform_of(source)
            self.table.setItem(row, 0, QTableWidgetItem(self._i18n.t(f"social.platform.{platform}", platform)))
            self.table.setItem(row, 1, QTableWidgetItem(source.name))
            url_item = QTableWidgetItem(source.url)
            url_item.setData(Qt.ItemDataRole.UserRole, source.id)
            self.table.setItem(row, 2, url_item)
        self._refresh_limit()
        self._sync_remove()

    def _refresh_limit(self) -> None:
        used = self._follow_count()
        self.limit_label.setText(
            self._i18n.t("social.limit")
            .replace("{used}", str(used))
            .replace("{max}", str(SOCIAL_FOLLOW_LIMIT))
        )

    def _follow_count(self) -> int:
        return sum(
            1
            for source in self._db.list_sources(active_only=False)
            if source.module_id == SOCIAL_MODULE_ID and source.user_added
        )

    def _apply_detected_platform(self, raw: str) -> str:
        detected = detect_platform(raw)
        if not detected:
            return str(self.platform.currentData() or "")
        idx = self.platform.findData(detected)
        if idx >= 0 and self.platform.currentIndex() != idx:
            self.platform.blockSignals(True)
            self.platform.setCurrentIndex(idx)
            self.platform.blockSignals(False)
            self._on_platform()
        return detected

    def _on_platform(self) -> None:
        platform = self.platform.currentData() or "youtube"
        self.add_btn.setEnabled(True)
        self.handle.setEnabled(True)
        self.handle.setPlaceholderText(self._i18n.t(f"social.placeholder.{platform}"))

    def _sync_remove(self) -> None:
        self.remove_btn.setEnabled(self._selected_id() is not None)

    def _selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 2)
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def _test(self) -> None:
        target = self._resolve_target()
        if target is None:
            return
        name, url = target
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = probe_source(url, is_rss=True, sample_limit=8)
        except Exception as exc:
            QMessageBox.warning(self, self._i18n.t("social.test_title"), str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()
        self._append_log(result.lines)
        samples = "\n".join(f"• {title}" for title in result.sample_titles) or self._i18n.t("social.test_empty")
        if result.ok:
            message = (
                self._i18n.t("social.test_ok")
                .replace("{name}", name)
                .replace("{count}", str(result.item_count))
                .replace("{samples}", samples)
            )
            QMessageBox.information(self, self._i18n.t("social.test_title"), message)
            return
        QMessageBox.warning(
            self,
            self._i18n.t("social.test_title"),
            self._i18n.t("social.test_fail")
            .replace("{name}", name)
            .replace("{error}", result.error or self._i18n.t("social.test_empty")),
        )

    def _append_log(self, lines: list[str]) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        block = "\n".join(f"[{stamp}] {line}" for line in lines if str(line).strip())
        if not block:
            return
        self.test_log.appendPlainText(block)
        self.test_log.appendPlainText("")
        scrollbar = self.test_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _resolve_target(self) -> tuple[str, str] | None:
        handle = self.handle.text().strip()
        if handle:
            platform = self._apply_detected_platform(handle)
            if platform not in SUPPORTED:
                QMessageBox.information(self, self._i18n.t("social.title"), self._i18n.t("social.unsupported"))
                return None
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                resolved = resolve_follow(platform, handle)
            except SocialResolveError as exc:
                QMessageBox.warning(
                    self,
                    self._i18n.t("social.title"),
                    self._i18n.t(f"social.error.{exc.code}", self._i18n.t("social.error.not_found")),
                )
                return None
            except Exception as exc:
                QMessageBox.warning(self, self._i18n.t("social.title"), str(exc))
                return None
            finally:
                QApplication.restoreOverrideCursor()
            return resolved.name, resolved.feed_url
        source_id = self._selected_id()
        if source_id is None:
            QMessageBox.information(self, self._i18n.t("social.title"), self._i18n.t("social.test_need_account"))
            return None
        source = self._db.get_source(source_id)
        if source is None:
            QMessageBox.information(self, self._i18n.t("social.title"), self._i18n.t("social.test_need_account"))
            return None
        return source.name, source.url

    def _add(self) -> None:
        platform = self._apply_detected_platform(self.handle.text())
        if platform not in SUPPORTED:
            QMessageBox.information(self, self._i18n.t("social.title"), self._i18n.t("social.unsupported"))
            return
        if self._follow_count() >= SOCIAL_FOLLOW_LIMIT:
            QMessageBox.information(self, self._i18n.t("social.title"), self._i18n.t("social.limit_reached"))
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            try:
                resolved = resolve_follow(platform, self.handle.text())
            except SocialResolveError as exc:
                QMessageBox.warning(
                    self,
                    self._i18n.t("social.title"),
                    self._i18n.t(f"social.error.{exc.code}", self._i18n.t("social.error.not_found")),
                )
                return
            except Exception as exc:
                QMessageBox.warning(self, self._i18n.t("social.title"), str(exc))
                return
        finally:
            QApplication.restoreOverrideCursor()
        try:
            self._db.add_user_source(
                name=resolved.name,
                url=resolved.feed_url,
                module_id=SOCIAL_MODULE_ID,
                is_rss=True,
                topic_id=resolved.topic_id,
            )
        except DuplicateSourceError:
            QMessageBox.information(self, self._i18n.t("social.title"), self._i18n.t("social.duplicate"))
            return
        except Exception as exc:
            QMessageBox.warning(self, self._i18n.t("social.title"), str(exc))
            return
        self.handle.clear()
        self._mark_changed()
        self.reload()

    def _remove(self) -> None:
        source_id = self._selected_id()
        if source_id is None:
            return
        if self._db.delete_user_source(source_id):
            self._mark_changed()
            self.reload()

    def _mark_changed(self) -> None:
        self.sources_changed = True
        dialog = self.window()
        if dialog is not None:
            setattr(dialog, "sources_changed", True)


def _platform_of(source: Source) -> str:
    topic = source.topic_id or ""
    for key, topic_id in TOPIC_IDS.items():
        if topic == topic_id or topic.startswith(f"{topic_id}."):
            return key
    url = source.url.lower()
    if "youtube" in url:
        return "youtube"
    if "substack" in url:
        return "substack"
    if "bsky" in url:
        return "bluesky"
    return "youtube"
