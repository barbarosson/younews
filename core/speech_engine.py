"""Windows TTS for news summaries. Match installed voices to the story language."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

from PySide6.QtCore import QLocale, QObject, Signal
from PySide6.QtGui import QTextDocument
from PySide6.QtTextToSpeech import QTextToSpeech, QVoice

MAX_SPEAK_CHARS = 2400
FEMALE_HINTS = (
    "zira", "hazel", "eva", "hedda", "katja", "haruka", "huihui", "susan",
    "linda", "helena", "laura", "emel", "hortense", "haruka", "female",
)
MALE_HINTS = (
    "david", "mark", "george", "stefan", "paul", "tolga", "james", "richard",
    "pablo", "hed", "ichiro", "kangkang", "male",
)
TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
LOCALE_FOR = {
    "tr": QLocale(QLocale.Language.Turkish, QLocale.Country.Turkey),
    "en": QLocale(QLocale.Language.English, QLocale.Country.UnitedStates),
    "es": QLocale(QLocale.Language.Spanish, QLocale.Country.Spain),
    "fr": QLocale(QLocale.Language.French, QLocale.Country.France),
    "de": QLocale(QLocale.Language.German, QLocale.Country.Germany),
    "pt": QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil),
    "ar": QLocale(QLocale.Language.Arabic, QLocale.Country.SaudiArabia),
    "ja": QLocale(QLocale.Language.Japanese, QLocale.Country.Japan),
    "zh": QLocale(QLocale.Language.Chinese, QLocale.Country.China),
}
APP_LANGUAGES = tuple(LOCALE_FOR.keys())
TR_WORDS = re.compile(
    r"\b(ve|bir|için|icin|olan|olarak|ancak|ile|daha|çok|cok|değil|degil|"
    r"haber|bugün|bugun|türkiye|turkiye|ekonomi|enflasyon)\b",
    re.IGNORECASE,
)
EN_WORDS = re.compile(r"\b(the|and|with|from|after|that|this|markets?|said|according)\b", re.IGNORECASE)
ES_WORDS = re.compile(r"\b(noticias|según|segun|economía|economia|después|despues|también|tambien)\b", re.IGNORECASE)
FR_WORDS = re.compile(r"\b(les|une|dans|pour|avec|france|économ|econom)\b", re.IGNORECASE)
DE_WORDS = re.compile(r"\b(und|nicht|nach|wirtschaft|deutschland|einer)\b", re.IGNORECASE)
PT_WORDS = re.compile(r"\b(não|nao|uma|são|sao|também|tambem|notícias|noticias)\b", re.IGNORECASE)


def plain_text(value: str) -> str:
    text = unescape(value or "")
    if "<" in text and ">" in text:
        document = QTextDocument()
        document.setHtml(text)
        text = document.toPlainText()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_speak_language(text: str, fallback: str) -> str:
    sample = text or ""
    if re.search(r"[\u0600-\u06FF]", sample):
        return "ar"
    if re.search(r"[\u3040-\u30FF]", sample):
        return "ja"
    if re.search(r"[\u4E00-\u9FFF]", sample):
        return "zh"
    if sum(1 for char in sample if char in "ğışİĞŞ") >= 1 or TR_WORDS.search(sample):
        return "tr"
    if "ß" in sample or DE_WORDS.search(sample):
        return "de"
    if any(char in sample for char in "ñ¿¡") or ES_WORDS.search(sample):
        return "es"
    if any(char in sample for char in "ãõ") or PT_WORDS.search(sample):
        return "pt"
    if FR_WORDS.search(sample) and re.search(r"[éèàùêôîç]", sample):
        return "fr"
    if EN_WORDS.search(sample):
        return "en"
    return (fallback or "en")[:2]


@dataclass
class VoiceChoice:
    engine: QTextToSpeech
    voice: QVoice
    language: str


class SpeechEngine(QObject):
    speaking_changed = Signal(bool)
    failed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._gender = "female"
        self._language = "en"
        self._engines: list[QTextToSpeech] = []
        self._catalog: list[VoiceChoice] = []
        self._tts: QTextToSpeech | None = None
        self._speaking = False
        self._queue: list[str] = []
        self._create()

    @property
    def available(self) -> bool:
        return bool(self._catalog)

    @property
    def speaking(self) -> bool:
        return self._speaking

    def installed_languages(self) -> list[str]:
        return sorted({item.language for item in self._catalog})

    def missing_languages(self) -> list[str]:
        have = set(self.installed_languages())
        return [code for code in APP_LANGUAGES if code not in have]

    def voices_for(self, language: str) -> list[str]:
        return sorted(
            {
                item.voice.name()
                for item in self._catalog
                if item.language == language
            }
        )

    def set_language(self, language: str) -> None:
        self._language = (language or "en")[:2]
        self._apply_voice(self._language)

    def set_gender(self, gender: str) -> None:
        self._gender = "male" if gender == "male" else "female"
        self._apply_voice(self._language)

    def speak(self, text: str) -> bool:
        cleaned = plain_text(text)
        if not cleaned:
            self.failed.emit("empty")
            return False
        if not self._catalog:
            self.failed.emit("unavailable")
            return False
        self._queue = _chunks(cleaned, MAX_SPEAK_CHARS)
        self._apply_voice(detect_speak_language(cleaned, self._language))
        if self._tts is None:
            self.failed.emit("unavailable")
            return False
        self._speak_next()
        return True

    def stop(self) -> None:
        self._queue = []
        for engine in self._engines:
            engine.stop()

    def _speak_next(self) -> None:
        if not self._queue or self._tts is None:
            return
        chunk = self._queue.pop(0)
        for engine in self._engines:
            engine.stop()
        self._tts.say(chunk)

    def _create(self) -> None:
        names = [str(item) for item in QTextToSpeech.availableEngines() if str(item) != "mock"]
        order = [item for item in ("winrt", "sapi") if item in names] + [
            item for item in names if item not in {"winrt", "sapi"}
        ]
        for name in order:
            try:
                engine = QTextToSpeech(name, self)
            except Exception:
                continue
            engine.stateChanged.connect(self._on_state)
            self._engines.append(engine)
            self._catalog.extend(_voices_for_engine(engine))
        if self._catalog:
            self._tts = self._catalog[0].engine
            self._apply_voice(self._language)

    def _apply_voice(self, language: str) -> None:
        language = (language or "en")[:2]
        choice = self._pick(language)
        if choice is None:
            return
        locale = LOCALE_FOR.get(choice.language)
        if locale is not None:
            choice.engine.setLocale(locale)
        choice.engine.setVoice(choice.voice)
        matched = _gender_of(choice.voice) == self._gender
        if matched:
            choice.engine.setPitch(0.0)
        else:
            choice.engine.setPitch(0.28 if self._gender == "female" else -0.12)
        self._tts = choice.engine

    def _pick(self, language: str) -> VoiceChoice | None:
        for lang in (language, "en"):
            pool = [item for item in self._catalog if item.language == lang]
            if not pool:
                continue
            ranked = sorted(pool, key=lambda item: self._score(item), reverse=True)
            return ranked[0]
        return self._catalog[0] if self._catalog else None

    def _score(self, item: VoiceChoice) -> int:
        name = (item.voice.name() or "").lower()
        score = 0
        gender = _gender_of(item.voice)
        if gender == self._gender:
            score += 12
        if self._gender == "female" and any(token in name for token in FEMALE_HINTS):
            score += 6
        if self._gender == "male" and any(token in name for token in MALE_HINTS):
            score += 6
        if "desktop" in name:
            score -= 1
        return score

    def _on_state(self, _state) -> None:
        speaking = any(engine.state() == QTextToSpeech.State.Speaking for engine in self._engines)
        if not speaking and self._queue:
            self._speak_next()
            speaking = True
        if speaking == self._speaking:
            return
        self._speaking = speaking
        self.speaking_changed.emit(speaking)


def _chunks(text: str, size: int) -> list[str]:
    if len(text) <= size:
        return [text]
    parts: list[str] = []
    rest = text
    while rest:
        if len(rest) <= size:
            parts.append(rest)
            break
        cut = rest.rfind(". ", 0, size)
        if cut < size // 2:
            cut = size
        else:
            cut += 1
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    return [part for part in parts if part]


def _gender_of(voice: QVoice) -> str:
    return "female" if voice.gender() == QVoice.Gender.Female else "male"


def _lang_of(voice: QVoice) -> str:
    return (voice.locale().name() or "").replace("-", "_")[:2].lower()


def _voices_for_engine(engine: QTextToSpeech) -> list[VoiceChoice]:
    found: list[VoiceChoice] = []
    seen: set[tuple[str, str]] = set()
    for language, locale in LOCALE_FOR.items():
        engine.setLocale(locale)
        for voice in engine.availableVoices():
            voice_lang = _lang_of(voice)
            if voice_lang != language:
                continue
            key = (voice.name(), voice_lang)
            if key in seen:
                continue
            seen.add(key)
            found.append(VoiceChoice(engine, voice, voice_lang))
    return found
