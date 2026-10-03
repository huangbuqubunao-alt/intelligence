import pytest

from youtube_intel.acoustic_scoring import coverage, score, text_units


def test_english_wer_and_repeatability():
    result = score("The local model keeps all media private.", "The local model keeps media private.", "en")
    assert result == score("The local model keeps all media private.", "The local model keeps media private.", "en")
    assert result["errors"] == 1 and result["reference_units"] == 7
    assert result["error_rate"] == pytest.approx(1 / 7)
    assert text_units("ＡＰＩ, don't!", "en") == ["api", "don't"]


def test_chinese_cer_preserves_characters_and_does_not_translate():
    assert score("模型在本地运行。", "模型在本地运转", "zh")["error_rate"] == pytest.approx(1 / 7)
    assert score("数据保存在本地", "The data stays local", "zh")["error_rate"] > 0.15
    assert text_units("你好，世界！", "zh") == list("你好世界")


def test_mixed_han_characters_and_latin_tokens():
    result = score("本地 API keeps media private。", "本地 API keeps media safe。", "mixed")
    assert result["reference_units"] == 6 and result["errors"] == 1
    assert result["han"]["error_rate"] == 0
    assert result["latin"]["error_rate"] == 0.25
    assert text_units("模型Whisper支持API", "mixed") == ["模", "型", "whisper", "支", "持", "api"]


def test_known_speech_omission_and_designed_silence():
    regions = [(0.5, 4.0), (10.0, 14.0)]
    complete = [(0.3, 4.3), (9.8, 14.2)]
    assert coverage(regions, complete)["passed"]
    omitted = coverage(regions, [(0.3, 4.3)])
    assert not omitted["passed"] and omitted["regions"][1]["uncovered_seconds"] == 4
    # A broad segment may conceal omission; textual utterance checks are independent.
    assert coverage(regions, [(0, 15)])["passed"]


def test_partial_large_gap_in_speech_fails():
    assert not coverage([(0, 10)], [(0, 2), (8, 10)])["passed"]
    assert coverage([(0, 10)], [(0.2, 9.8)])["passed"]


def test_empty_reference_is_not_a_fake_pass():
    with pytest.raises(ValueError):
        score("...", "hello", "en")
