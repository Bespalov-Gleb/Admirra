"""Каталог моделей ассистента и построение unified-reasoning payload OpenRouter.

Слаги — нон-дата алиасы OpenRouter (авто-последняя версия), сверены с
публичным https://openrouter.ai/api/v1/models. При подключении ключа их можно
поправить здесь или переопределить одним слагом через OPENROUTER_DEFAULT_MODEL.

OpenRouter reasoning API (docs/use-cases/reasoning-tokens):
  reasoning: { effort: "max|xhigh|high|medium|low|minimal|none", max_tokens, exclude }
Effort работает для GPT-5/Grok напрямую; для Anthropic/Gemini/Qwen OpenRouter
сам маппит effort в бюджет токенов. Мы шлём единый effort для всех моделей —
неподдержанные параметры OpenRouter игнорирует.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# Уровни «глубины размышлений» в UI. Пустая строка/none — размышления выключены.
EFFORT_LEVELS: tuple[str, ...] = ("none", "low", "medium", "high")
DEFAULT_EFFORT: str = "medium"


@dataclass(frozen=True)
class ModelSpec:
    id: str            # стабильный ключ для фронта и БД (ai_conversations.model)
    label: str         # отображаемое имя
    slug: str          # слаг в форме OpenRouter (provider/model)
    reasoning: bool    # доступен ли выбор effort
    family: str        # маршрут у ProxyAPI: anthropic | openai | openrouter
    description: str = ""
    efforts: tuple[str, ...] = field(default=EFFORT_LEVELS)
    default_effort: str = DEFAULT_EFFORT

    @property
    def native_name(self) -> str:
        """Имя модели без префикса провайдера (для нативных эндпоинтов
        ProxyAPI /openai и /anthropic). Для openrouter-маршрута шлём полный слаг."""
        return self.slug.split("/", 1)[-1]


# Порядок = порядок в селекторе. Первый элемент — модель по умолчанию.
MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="claude-sonnet-5",
        label="Claude Sonnet 5",
        slug="anthropic/claude-sonnet-5",
        reasoning=True,
        family="anthropic",
        description="Быстрая и сбалансированная — дефолт для аналитики.",
    ),
    ModelSpec(
        id="claude-opus-5",
        label="Claude Opus 5",
        slug="anthropic/claude-opus-5",
        reasoning=True,
        family="anthropic",
        description="Максимально глубокая для сложных разборов.",
    ),
    ModelSpec(
        id="gpt-5.6-terra",
        label="GPT-5.6 Terra",
        slug="openai/gpt-5.6-terra",
        reasoning=True,
        family="openai",
        description="Флагман OpenAI, сильная в рассуждениях и инструментах.",
    ),
    ModelSpec(
        id="gpt-5.6-sol",
        label="Sol 5.6",
        slug="openai/gpt-5.6-sol",
        reasoning=True,
        family="openai",
        description="Быстрый вариант линейки GPT-5.6.",
    ),
    ModelSpec(
        id="kimi-k3",
        label="Kimi K3",
        slug="moonshotai/kimi-k3",
        reasoning=True,
        family="openrouter",
        description="Moonshot Kimi — длинный контекст и инструменты.",
    ),
)

DEFAULT_MODEL_ID: str = MODELS[0].id

_BY_ID: dict[str, ModelSpec] = {m.id: m for m in MODELS}


def get_model(model_id: Optional[str]) -> ModelSpec:
    """Модель по id; при неизвестном/пустом — модель по умолчанию."""
    return _BY_ID.get((model_id or "").strip(), MODELS[0])


def normalize_effort(model: ModelSpec, effort: Optional[str]) -> Optional[str]:
    """Валидный effort для модели: приводит к допустимому набору или к дефолту.
    Возвращает None, если размышления моделью не поддерживаются."""
    if not model.reasoning:
        return None
    value = (effort or "").strip().lower()
    if value in model.efforts:
        return value
    return model.default_effort


def catalog_public() -> list[dict]:
    """Сериализация каталога для фронта (эндпоинт GET /ai/models)."""
    return [
        {
            "id": m.id,
            "label": m.label,
            "description": m.description,
            "reasoning": m.reasoning,
            "efforts": list(m.efforts) if m.reasoning else [],
            "default_effort": m.default_effort if m.reasoning else None,
        }
        for m in MODELS
    ]
