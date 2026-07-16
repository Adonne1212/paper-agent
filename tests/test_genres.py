import pytest

from paper_agent.genres import profile_for
from paper_agent.models import Genre


@pytest.mark.parametrize("genre", list(Genre))
def test_every_supported_genre_has_a_complete_profile(genre: Genre) -> None:
    profile = profile_for(genre)
    assert len(profile) >= 5
    assert abs(sum(section.ratio for section in profile) - 1.0) < 1e-9
    assert all(section.title and section.purpose for section in profile)
    assert all(0 < section.ratio < 0.5 for section in profile)
