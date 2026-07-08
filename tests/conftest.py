import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--update-goldens",
        action="store_true",
        default=False,
        help="re-freeze the golden SVG files instead of comparing against them",
    )


@pytest.fixture
def update_goldens(request):
    return request.config.getoption("--update-goldens")
