import os
import sys
import pytest
import subprocess
import time
import signal
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


@dataclass
class ServerFixture:
    port: int
    process: Any
    api_key: str
    model: str = field(default=None)
    db_url: str = field(default=None)


def get_test_params():
    """Return test parameters based on environment."""
    if os.environ.get("GITHUB_ACTIONS"):
        return [
            ".postgres.env",
        ]
    return [
        ".postgres.env",
        ".sqlite.env",
        ".mysql.env",
    ]

@pytest.fixture(
    scope="session",
    params=get_test_params()
)
def server_config(request):
    """Fixture that starts the LM-Proxy server for testing and stops it after tests complete."""
    root = Path(__file__).resolve().parent.parent
    # Shared .env file
    shared_env_path = root / ".env"
    load_dotenv(shared_env_path, override=True)
    test_env_path = root / "tests" / "env" / request.param
    load_dotenv(test_env_path, override=True)
    db_url = os.environ.get("DB_URL")
    print("Using DB_URL:", db_url)

    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS llm_logs;"))

    test_config_path = Path("tests/config.yml")
    server_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "lm_proxy",
            "--config",
            str(test_config_path),
            "--env",
            str(test_env_path),
            "--debug"
        ],
    )
    time.sleep(5)
    yield ServerFixture(
        port=int(os.environ.get("PORT")),
        process=server_process,
        model="any-model",
        api_key="py-test-key",
        db_url=db_url,
    )

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS llm_logs;"))

    server_process.send_signal(signal.SIGTERM)
    server_process.wait()
