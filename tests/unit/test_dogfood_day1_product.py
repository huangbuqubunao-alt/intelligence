"""Frozen Day 1 product contracts over schema-34 authority."""
import json
from pathlib import Path

import pytest
from test_local_api import _app

from youtube_intel.following_provider import TrackingError
from youtube_intel.local_api import ApiError
from youtube_intel.orchestration import (
    ProcessingPolicy,
    SourceType,
    normalize_source_url,
)
from youtube_intel.providers.youtube_channel import channel_input


@pytest.mark.parametrize('value', ['@example', 'https://www.youtube.com/@example', 'https://www.youtube.com/@example/videos', 'UC_x5XG1OV2P6uZZ5FSM9Ttw', 'https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw/videos'])
def test_channel_recognition_normalizes_safe_tabs(value: str) -> None:
    identity = channel_input(value)
    assert identity == ('@example' if 'example' in value else 'UC_x5XG1OV2P6uZZ5FSM9Ttw')
    normalized = normalize_source_url(value)
    assert normalized.source_type is SourceType.CHANNEL
    assert not normalized.canonical_url.endswith('/videos')


@pytest.mark.parametrize('value', ['https://youtube.com.evil.test/@example', 'http://youtube.com/@example', 'https://youtube.com/@example/evil', 'https://youtube.com/@example/videos?bad=1'])
def test_unsafe_channel_never_recognized(value: str) -> None:
    with pytest.raises(TrackingError):
        channel_input(value)


@pytest.mark.parametrize('value', ['https://www.youtube.com/watch?v=abcdefghijk', 'https://youtu.be/abcdefghijk', 'https://www.youtube.com/shorts/abcdefghijk', 'https://www.youtube.com/live/abcdefghijk'])
def test_video_recognition_never_implies_following(value: str) -> None:
    assert normalize_source_url(value).source_type is SourceType.VIDEO_URL
    assert normalize_source_url(value).video_id == 'abcdefghijk'


def test_product_policy_uses_existing_schema_authority() -> None:
    assert ProcessingPolicy.from_product_mode('ORGANIZE_CONTENT') is ProcessingPolicy.DISCOVER_ONLY
    assert ProcessingPolicy.from_product_mode('EXTRACT_INTELLIGENCE') is ProcessingPolicy.STANDARD_INTELLIGENCE
    assert ProcessingPolicy.DISCOVER_ONLY.product_mode == 'ORGANIZE_CONTENT'
    assert ProcessingPolicy.STANDARD_INTELLIGENCE.product_mode == 'EXTRACT_INTELLIGENCE'


def test_real_durable_import_identity_visible_before_metadata(tmp_path: Path) -> None:
    app = _app(tmp_path)
    source = app._service.add_source(url='https://youtu.be/abcdefghijk', processing_policy=ProcessingPolicy.DISCOVER_ONLY)
    status, payload = app.handle('GET', '/api/v1/videos')
    assert status == 200
    assert len(payload['videos']) == 1
    work = payload['videos'][0]
    assert work['video_id'] == source.video_id
    assert work['work_kind'] == 'DURABLE_CONTENT_IDENTITY'
    assert work['processing_status'] == 'WAITING'
    assert app._repository.list_videos() == ()  # Project a real work item, not fake Video metadata.
    detail = app.handle('GET', '/api/v1/videos/abcdefghijk')[1]
    assert detail['video'] == work
    assert detail['intelligence_result']['status'] == 'NOT_PROCESSED'
    assert app._repository.list_source_subscriptions()[0].source_type is SourceType.VIDEO_URL
    with app._repository._connect() as connection:
        assert connection.execute('select count(*) from source_tracking_state').fetchone()[0] == 0
        assert connection.execute('pragma user_version').fetchone()[0] == 36


def test_unavailable_tracking_does_not_create_generic_channel(tmp_path: Path) -> None:
    app = _app(tmp_path)
    app._source_tracking = None
    with pytest.raises(ApiError, match='no unresolved source'):
        app.handle('POST', '/api/v1/sources', json.dumps({'url': 'https://www.youtube.com/@example', 'processing_policy': 'DISCOVER_ONLY'}).encode())
    assert app._repository.list_source_subscriptions() == ()
