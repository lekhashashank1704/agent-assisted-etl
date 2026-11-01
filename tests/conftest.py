"""Isolated file-backed databases; verification never requires live API access."""

import socket

import pytest

from etl_agents.pipeline import Pipeline


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Network access is disabled in tests; use a mock transport")

    monkeypatch.setattr(socket.socket, "connect", blocked)


@pytest.fixture
def pipe(tmp_path):
    with Pipeline(tmp_path / "test.db") as pipeline:
        yield pipeline
