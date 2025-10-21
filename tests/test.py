import requests
from tests.conftest import ServerFixture
from sqlalchemy import create_engine, text


def test_direct_api_call(server_config: ServerFixture):
    """Test directly calling the API without microcore."""
    response = requests.post(
        f"http://127.0.0.1:{server_config.port}/v1/chat/completions",
        json={
            "model": server_config.model,
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
        },
        headers={
            "Content-Type": "application/json",
            "authorization": f"bearer {server_config.api_key}",
        },
    )

    assert (
        response.status_code == 200
    ), f"Expected status code 200, got {response.status_code}"

    data = response.json()
    assert "choices" in data, f"Missing 'choices' in response: {data}"
    assert len(data["choices"]) > 0, "No choices returned"
    assert (
        "message" in data["choices"][0]
    ), f"Missing 'message' in first choice: {data['choices'][0]}"
    assert (
        "Paris" in data["choices"][0]["message"]["content"]
    ), f"Expected 'Paris' in response, got: {data['choices'][0]['message']['content']}"

    engine = create_engine(server_config.db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM llm_logs"))
        count = result.scalar()
        assert count == 1, "incorrect llm_logs count"
