"""Finite audit identities only; membership grants no execution eligibility."""

from typing import Final

ZHIPU_PAIR: Final = ("zhipu_bigmodel", "glm-4.7-flash")
ZHIPU_AUTHORIZATIONS: Final = "distillation_zhipu_cloud_authorizations"
ZHIPU_FAILURES: Final = "distillation_zhipu_cloud_response_failures"
CLOUD_PROVIDERS: Final = frozenset({"nvidia_nim", "openai", "moonshot", ZHIPU_PAIR[0]})
CLOUD_FAILURE_TABLES: Final = ("distillation_cloud_response_failures", ZHIPU_FAILURES)
