"""TASK-016B scoring output-language contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

import youtube_intel.domain as domain_module
from youtube_intel.config import LocalScoringSettings
from youtube_intel.domain import (
    Availability,
    LiveStatus,
    ScoreResult,
    ScoringLanguageValidation,
    ScoringOutputLanguage,
    VideoMetadata,
    detect_scoring_language_violation,
    validate_score_result,
)
from youtube_intel.scoring import (
    InMemoryScoringCache,
    ScoringService,
    build_scoring_input,
)


def _settings() -> LocalScoringSettings:
    return LocalScoringSettings(
        model="qwen3:8b",
        expected_model_digest="sha256:" + ("a" * 64),
    )


def _video() -> VideoMetadata:
    return VideoMetadata(
        video_id="video-123",
        channel_id="channel-123",
        channel_name="Example Channel",
        title="A useful title",
        source_url="https://example.invalid/watch?v=video-123",
        published_at=datetime(2026, 8, 13, tzinfo=UTC),
        duration_seconds=120,
        live_status=LiveStatus.NONE,
        availability=Availability.PUBLIC,
    )


@pytest.mark.parametrize("output_language", ["zh-CN", "en"])
def test_scoring_input_contains_output_language(output_language: str) -> None:
    scoring_input = build_scoring_input(
        video=_video(),
        transcript_text="A sufficiently long canonical transcript.",
        language="en",
        output_language=output_language,
        settings=_settings(),
    )

    assert scoring_input.output_language == output_language


def test_output_language_changes_request_hash() -> None:
    common = {
        "video": _video(),
        "transcript_text": "A sufficiently long canonical transcript.",
        "language": "en",
        "settings": _settings(),
    }

    zh = build_scoring_input(output_language="zh-CN", **common)
    en = build_scoring_input(output_language="en", **common)

    assert zh.request_hash != en.request_hash


@pytest.mark.parametrize(
    ("output_language", "reason", "expected"),
    [
        (
            "zh-CN",
            "Useful clear practical workflow advice",
            ScoringLanguageValidation.UNCERTAIN,
        ),
        (
            "zh-CN",
            "该视频介绍 API、SDK、LLM 技术流程",
            ScoringLanguageValidation.VALID,
        ),
        (
            "zh-CN",
            "good nice happy 中文",
            ScoringLanguageValidation.UNCERTAIN,
        ),
        (
            "en",
            "这个视频详细解释产品流程",
            ScoringLanguageValidation.INVALID,
        ),
        (
            "en",
            "This video explains API and LLM workflow.",
            ScoringLanguageValidation.VALID,
        ),
        (
            "en",
            "clear 中文 advice",
            ScoringLanguageValidation.UNCERTAIN,
        ),
        ("zh-CN", "中", ScoringLanguageValidation.UNCERTAIN),
        ("en", "a", ScoringLanguageValidation.UNCERTAIN),
        (
            "en",
            "Useful practical advice",
            ScoringLanguageValidation.UNCERTAIN,
        ),
        ("en", "API SDK LLM", ScoringLanguageValidation.UNCERTAIN),
        (
            "zh-CN",
            "中 REST CUDA NLP CNN",
            ScoringLanguageValidation.UNCERTAIN,
        ),
        (
            "en",
            "a API SDK LLM GPT MLX",
            ScoringLanguageValidation.UNCERTAIN,
        ),
        (
            "zh-CN",
            "この動画はAPIの製品ワークフローを詳しく説明します。",
            ScoringLanguageValidation.UNCERTAIN,
        ),
        ("zh-CN", "中文かな", ScoringLanguageValidation.UNCERTAIN),
        ("zh-CN", "中文カナ", ScoringLanguageValidation.UNCERTAIN),
        ("zh-CN", "中文한글", ScoringLanguageValidation.UNCERTAIN),
        ("zh-CN", "中文русский", ScoringLanguageValidation.UNCERTAIN),
        ("zh-CN", "中文العربية", ScoringLanguageValidation.UNCERTAIN),
    ],
)
def test_language_violation_detector_returns_three_state_result(
    output_language: ScoringOutputLanguage,
    reason: str,
    expected: ScoringLanguageValidation,
) -> None:
    assert detect_scoring_language_violation(reason, output_language) is expected


@pytest.mark.parametrize(
    ("output_language", "reason"),
    [
        ("zh-CN", "The video gives a detailed practical explanation of the product workflow."),
        ("zh-CN", "Useful, clear, practical, product, workflow, advice."),
        ("zh-CN", "Useful, clear, practical, product, workflow, advice. 中"),
        (
            "zh-CN",
            "The video clearly explains the product workflow and gives useful advice.\n中",
        ),
        (
            "zh-CN",
            "Useful clear practical product workflow advice.\n"
            "这个视频介绍产品流程。",
        ),
        (
            "zh-CN",
            "中 Useful clear practical product workflow advice 中",
        ),
        (
            "zh-CN",
            "中文 Useful clear practical product workflow advice 中文",
        ),
        ("en", "这个视频清晰完整地解释了产品流程，并给出了可以直接执行的建议。"),
        ("en", "这个视频详细解释了 API、SDK、LLM、RAG、GPT 和 MLX 的产品工作流程。"),
        ("en", "这个视频详细解释了 api、sdk、llm 的产品工作流程。"),
        (
            "en",
            "这个视频详细解释了产品工作流程并给出了建议。\n"
            "Useful clear practical product workflow advice.",
        ),
        ("en", "a 这个视频详细解释产品流程 a"),
        ("en", "a clear 这个视频详细解释产品流程 advice"),
        ("en", "The 北京大学人工智能实验室 team clearly explains the product workflow."),
        ("en", "API SDK LLM"),
    ],
)
def test_score_result_rejects_obvious_wrong_language(
    output_language: str,
    reason: str,
) -> None:
    with pytest.raises(ValueError):
        ScoreResult(
            schema_version="score-result-v2",
            score=8,
            reason=reason,
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v2",
            request_hash="a" * 64,
            output_language=output_language,
        )


@pytest.mark.parametrize(
    "reason",
    [
        "Amazon Connect Salesforce",
        "Docker Kubernetes Terraform Ansible",
        "docker kubernetes terraform ansible",
        "Docker Terraform Kubernetes Ansible",
        "Redis Kafka PostgreSQL MongoDB",
        "redis kafka postgresql mongodb",
        "REST CUDA NLP CNN",
        "APIs SDKs LLMs GPTs MLXs",
        "OpenAI PyTorch TensorFlow Kubernetes",
        "この動画はAPIの製品ワークフローを詳しく説明します。",
    ],
)
def test_technical_identifiers_and_non_chinese_scripts_cannot_prove_language(
    reason: str,
) -> None:
    assert (
        detect_scoring_language_violation(
            reason,
            "zh-CN" if "動画" in reason else "en",
        )
        is ScoringLanguageValidation.UNCERTAIN
    )
    with pytest.raises(ValueError):
        ScoreResult(
            schema_version="score-result-v2",
            score=8,
            reason=reason,
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v2",
            request_hash="a" * 64,
            output_language="zh-CN" if "動画" in reason else "en",
        )


@pytest.mark.parametrize(
    "reason",
    [
        "Kubernetes orchestrates Docker",
        "kubernetes orchestrates docker",
        "KUBERNETES ORCHESTRATES DOCKER",
    ],
)
def test_bare_entity_arguments_do_not_become_language_evidence(reason: str) -> None:
    assert (
        detect_scoring_language_violation(reason, "en")
        is ScoringLanguageValidation.UNCERTAIN
    )
    with pytest.raises(ValueError):
        ScoreResult(
            schema_version="score-result-v2",
            score=8,
            reason=reason,
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v2",
            request_hash="a" * 64,
            output_language="en",
        )


@pytest.mark.parametrize(
    "reason",
    [
        "Amazon Connect General Electric",
        "Amazon Connect National Geographic",
        "Amazon Connect Meta Platforms",
        "Amazon Connect Advanced Micro Devices",
        "Amazon Connect Red Bull",
        "Amazon Connect Whole Foods Market",
        "Amazon Connect General Motors",
        "Amazon Connect Federal Express",
        "Amazon Connect Jack in the Box",
        "Amazon Connect The Home Depot",
        "Amazon Connect The North Face",
        "Amazon Connect The Weather Channel",
        "Amazon Connect The New York Times",
        "The Home Depot",
        "The North Face",
        "amazon connect the home depot",
        "AMAZON CONNECT THE HOME DEPOT",
    ],
)
def test_named_entity_spans_cannot_be_mistaken_for_predicate_structure(
    reason: str,
) -> None:
    assert (
        detect_scoring_language_violation(reason, "en")
        is ScoringLanguageValidation.UNCERTAIN
    )
    with pytest.raises(ValueError):
        ScoreResult(
            schema_version="score-result-v2",
            score=8,
            reason=reason,
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v2",
            request_hash="a" * 64,
            output_language="en",
        )


@pytest.mark.parametrize(
    "reason",
    [
        "This Video Explains Machine Learning Workflows Clearly",
        "OpenAI Develops Useful AI Models",
    ],
)
def test_title_case_english_natural_language_is_valid(reason: str) -> None:
    assert (
        detect_scoring_language_violation(reason, "en")
        is ScoringLanguageValidation.VALID
    )
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8,
        reason=reason,
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="en",
    )
    assert result.reason == reason


def test_missing_local_dependency_model_is_uncertain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    domain_module._load_english_dependency_parser.cache_clear()

    def _missing_package(_: str) -> object:
        raise ImportError("fixed local model is unavailable")

    monkeypatch.setattr(domain_module, "import_module", _missing_package)
    try:
        assert (
            detect_scoring_language_violation(
                "This video explains useful product workflows clearly.",
                "en",
            )
            is ScoringLanguageValidation.UNCERTAIN
        )
    finally:
        domain_module._load_english_dependency_parser.cache_clear()


@pytest.mark.parametrize(
    "reason",
    [
        "Docker containers help developers deploy applications",
        "docker containers help developers deploy applications",
        "DOCKER CONTAINERS HELP DEVELOPERS DEPLOY APPLICATIONS",
        "The system relies on Docker for deployment.",
        "the system relies on docker for deployment.",
        "THE SYSTEM RELIES ON DOCKER FOR DEPLOYMENT.",
        "Redis stores data and improves application performance",
        "redis stores data and improves application performance",
        "REDIS STORES DATA AND IMPROVES APPLICATION PERFORMANCE",
        "OpenAI develops useful AI models",
        "openai develops useful ai models",
        "OPENAI DEVELOPS USEFUL AI MODELS",
    ],
)
def test_technical_entity_with_english_relation_structure_is_valid(
    reason: str,
) -> None:
    assert (
        detect_scoring_language_violation(reason, "en")
        is ScoringLanguageValidation.VALID
    )
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8,
        reason=reason,
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="en",
    )
    assert result.reason == reason


def test_parser_ambiguous_short_clause_remains_uncertain() -> None:
    reason = "Redis stores data"
    assert (
        detect_scoring_language_violation(reason, "en")
        is ScoringLanguageValidation.UNCERTAIN
    )
    with pytest.raises(ValueError):
        ScoreResult(
            schema_version="score-result-v2",
            score=8,
            reason=reason,
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v2",
            request_hash="a" * 64,
            output_language="en",
        )


@pytest.mark.parametrize(
    "reason",
    [
        "Docker helps",
        "Redis stores",
        "OpenAI develops",
    ],
)
def test_incomplete_english_predicate_is_uncertain(reason: str) -> None:
    assert (
        detect_scoring_language_violation(reason, "en")
        is ScoringLanguageValidation.UNCERTAIN
    )
    with pytest.raises(ValueError):
        ScoreResult(
            schema_version="score-result-v2",
            score=8,
            reason=reason,
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v2",
            request_hash="a" * 64,
            output_language="en",
        )


def test_chinese_natural_language_with_technical_identifiers_is_valid() -> None:
    reason = "该视频介绍 GPT API 调用流程"
    assert (
        detect_scoring_language_violation(reason, "zh-CN")
        is ScoringLanguageValidation.VALID
    )
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8,
        reason=reason,
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="zh-CN",
    )
    assert result.reason == reason


def test_chinese_reason_allows_english_technical_terms() -> None:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8,
        reason="视频清楚说明了 GPT、API、MLX 与 Ollama 的组合方式，具有实际参考价值。",
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="zh-CN",
    )

    assert result.output_language == "zh-CN"


def test_chinese_subject_with_technical_abbreviations_is_valid() -> None:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8,
        reason="视频说明了 API、SDK、LLM 和 MLX 的产品工作流程，并给出实用建议。",
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="zh-CN",
    )

    assert result.output_language == "zh-CN"


@pytest.mark.parametrize(
    ("output_language", "reason"),
    [
        ("zh-CN", "该视频介绍 API、SDK、LLM、MLX 技术流程。"),
        ("en", "This video explains API, SDK and LLM workflow clearly."),
    ],
)
def test_continuous_subject_survives_technical_term_stripping(
    output_language: ScoringOutputLanguage,
    reason: str,
) -> None:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8,
        reason=reason,
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language=output_language,
    )

    assert result.reason == reason


def test_english_phrase_without_predicate_is_uncertain() -> None:
    reason = "Useful clear practical product workflow advice."

    assert (
        detect_scoring_language_violation(reason, "en")
        is ScoringLanguageValidation.UNCERTAIN
    )
    with pytest.raises(ValueError):
        ScoreResult(
            schema_version="score-result-v2",
            score=8,
            reason=reason,
            topics=("product",),
            should_summarize=True,
            provider="ollama",
            model="qwen3:8b",
            prompt_version="scoring-prompt-v2",
            request_hash="a" * 64,
            output_language="en",
        )


def test_english_reason_allows_technical_terms() -> None:
    reason = "API, SDK, LLM, RAG, GPT, and MLX provide useful technical context."
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8,
        reason=reason,
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="en",
    )

    assert result.reason == reason


def test_score_result_rejects_unchecked_output_language_copy() -> None:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8,
        reason="视频清楚说明了产品工作流，因此具有实际参考价值。",
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="zh-CN",
    )

    with pytest.raises(ValueError, match=r"model_copy\(update=\.\.\.\) is disabled"):
        result.model_copy(update={"output_language": "en"})


@pytest.mark.parametrize("unchecked_factory", ["copy", "construct"])
def test_trusted_score_validation_rejects_unchecked_language_mutation(
    unchecked_factory: str,
) -> None:
    result = ScoreResult(
        schema_version="score-result-v2",
        score=8,
        reason="视频清楚说明了产品工作流程，因此具有实际参考价值。",
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="zh-CN",
    )
    payload = {**result.model_dump(mode="python"), "output_language": "en"}
    if unchecked_factory == "copy":
        with pytest.warns(DeprecationWarning):
            unchecked = result.copy(update={"output_language": "en"})
    else:
        unchecked = ScoreResult.model_construct(**payload)

    with pytest.raises(ValueError, match="reason does not match output_language"):
        validate_score_result(unchecked)


def test_in_memory_cache_revalidates_unchecked_score_result() -> None:
    unchecked = ScoreResult.model_construct(
        schema_version="score-result-v2",
        score=8,
        reason="视频清楚说明了产品工作流程，因此具有实际参考价值。",
        topics=("product",),
        should_summarize=True,
        provider="ollama",
        model="qwen3:8b",
        prompt_version="scoring-prompt-v2",
        request_hash="a" * 64,
        output_language="en",
    )

    with pytest.raises(ValueError, match="reason does not match output_language"):
        InMemoryScoringCache().put(unchecked)


def test_scoring_service_revalidates_unchecked_provider_result_before_cache() -> None:
    class _UncheckedProvider:
        def score(self, scoring_input: object) -> ScoreResult:
            return ScoreResult.model_construct(
                schema_version="score-result-v2",
                score=8,
                reason="这个视频详细解释了产品工作流程。",
                topics=("product",),
                should_summarize=True,
                provider="ollama",
                model="qwen3:8b",
                prompt_version="scoring-prompt-v2",
                request_hash=getattr(scoring_input, "request_hash"),
                output_language="en",
            )

    cache = InMemoryScoringCache()
    service = ScoringService(
        provider=_UncheckedProvider(),
        settings=_settings(),
        summary_threshold=7,
        cache=cache,
    )

    with pytest.raises(ValueError, match="reason does not match output_language"):
        service.score(
            video=_video(),
            transcript_text="canonical transcript",
            language="en",
            output_language="en",
        )

    assert cache._results == {}


def test_result_language_mismatch_is_not_cached() -> None:
    class _WrongLanguageProvider:
        calls = 0

        def score(self, scoring_input: object) -> ScoreResult:
            self.calls += 1
            return ScoreResult(
                schema_version="score-result-v2",
                score=8,
                reason="This video gives a useful explanation of the product workflow.",
                topics=("product",),
                should_summarize=True,
                provider="ollama",
                model="qwen3:8b",
                prompt_version="scoring-prompt-v2",
                request_hash=getattr(scoring_input, "request_hash"),
                output_language="en",
            )

    provider = _WrongLanguageProvider()
    cache = InMemoryScoringCache()
    service = ScoringService(
        provider=provider,
        settings=_settings(),
        summary_threshold=7,
        cache=cache,
    )

    with pytest.raises(ValueError, match="output language"):
        service.score(
            video=_video(),
            transcript_text="canonical transcript",
            language="en",
            output_language="zh-CN",
        )

    assert provider.calls == 1
    assert cache._results == {}


@pytest.mark.parametrize(
    ("first_language", "second_language"),
    [("zh-CN", "en"), ("en", "zh-CN")],
)
def test_cache_is_not_reused_across_output_languages(
    first_language: str,
    second_language: str,
) -> None:
    class _LanguageProvider:
        calls = 0

        def score(self, scoring_input: object) -> ScoreResult:
            self.calls += 1
            output_language = getattr(scoring_input, "output_language")
            reason = (
                "视频清楚说明了产品工作流，因此具有实际参考价值。"
                if output_language == "zh-CN"
                else "The video clearly explains the product workflow and has practical value."
            )
            return ScoreResult(
                schema_version="score-result-v2",
                score=8,
                reason=reason,
                topics=("product",),
                should_summarize=True,
                provider="ollama",
                model="qwen3:8b",
                prompt_version="scoring-prompt-v2",
                request_hash=getattr(scoring_input, "request_hash"),
                output_language=output_language,
            )

    provider = _LanguageProvider()
    cache = InMemoryScoringCache()
    for output_language in (first_language, second_language):
        service = ScoringService(
            provider=provider,
            settings=_settings(),
            summary_threshold=7,
            cache=cache,
        )
        service.score(
            video=_video(),
            transcript_text="canonical transcript",
            language="en",
            output_language=output_language,
        )

    assert provider.calls == 2


def test_valid_language_bound_cache_uses_zero_additional_provider_calls() -> None:
    class _LanguageProvider:
        calls = 0

        def score(self, scoring_input: object) -> ScoreResult:
            self.calls += 1
            return ScoreResult(
                schema_version="score-result-v2",
                score=8,
                reason="视频清楚说明了产品工作流，因此具有实际参考价值。",
                topics=("product",),
                should_summarize=True,
                provider="ollama",
                model="qwen3:8b",
                prompt_version="scoring-prompt-v2",
                request_hash=getattr(scoring_input, "request_hash"),
                output_language="zh-CN",
            )

    provider = _LanguageProvider()
    service = ScoringService(
        provider=provider,
        settings=_settings(),
        summary_threshold=7,
        cache=InMemoryScoringCache(),
    )

    first = service.score(
        video=_video(), transcript_text="canonical transcript", language="en",
        output_language="zh-CN",
    )
    second = service.score(
        video=_video(), transcript_text="canonical transcript", language="en",
        output_language="zh-CN",
    )

    assert provider.calls == 1
    assert first.result == second.result
    assert [entry.code for entry in second.call.diagnostics] == ["CACHE_HIT"]
