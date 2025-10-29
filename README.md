# LM Proxy Database Connector

![Coverage](coverage.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13-blue)](https://www.python.org/)
[![Code Style](https://github.com/Nayjest/lm-proxy-db-connector/actions/workflows/code-style.yml/badge.svg)](https://github.com/Nayjest/lm-proxy-db-connector/actions)
[![Build Status](https://github.com/Nayjest/lm-proxy-db-connector/actions/workflows/tests.yml/badge.svg)](https://github.com/Nayjest/lm-proxy-db-connector/actions)

A minimalistic SQLAlchemy-based database connector for [LM-Proxy](https://github.com/Nayjest/lm-proxy).

## Features

- 📊 Database connection management with SQLAlchemy
- 📝 Includes a component for logging of LLM requests and responses to various databases
- 🔄 Support for SQLite, PostgreSQL, MySQL, and other SQLAlchemy-supported databases
- 🛡️ Thread-safe implementation

## Installation

```bash
pip install lm-proxy-db-connector
```

## Quick Start

### Using with LM-Proxy

Add the DB component to your LM-Proxy configuration:

```toml
# config.toml
[components.db]
dsn = "postgresql+psycopg2://user:password@localhost:5432/mydb"
class = "lm_proxy_db_connector.init_db"

# Add database logging
[[loggers]]
class = "lm_proxy.loggers.BaseLogger"
[loggers.log_writer]
class = "lm_proxy_db_connector.logging.DBLogWriter"
table_name = "llm_logs"
```

### Using with YAML config

```yaml
# config.yml
components:
  db:
    class: "lm_proxy_db_connector.init_db"
    db_url: "postgresql+psycopg2://user:password@localhost:5432/mydb"

loggers:
  - class: "lm_proxy_db_connector.logging.DBLogger"
    table_name: "llm_logs"
```

### Supported Database URLs

The connector uses SQLAlchemy's URL format:

- SQLite: `sqlite:///path/to/database.db` or `sqlite:///:memory:` (in-memory)
- PostgreSQL: `postgresql+psycopg2://user:password@localhost:5432/dbname`
- MySQL: `mysql+pymysql://user:password@localhost:3306/dbname`

### Database Session Usage

```python
from lm_proxy_db_connector import db_session
# DB initialization is handled by the LM Proxy component

# Use a session
with db_session() as session:
    result = session.execute("SELECT * FROM users")
    # Session is automatically committed or rolled back
```

### Database Logger

```python
from lm_proxy_db_connector.logging import DBLogger

# Create a logger that logs to a database table
logger = DBLogger(
    table_name="llm_logs",
    schema="public",  # Optional
    # Define column structure and mapping
    columns={
        "id": {"type": "string", "primary_key": True, "length": 36},
        "request": {"type": "json", "src": "request.messages"},
        "response": {"type": "text"},
        "created_at": {"type": "datetime", "default": "now"},
        # Completion tokens extracted from response.usage
        "completion_tokens": {"type": "integer", "src": "response.usage.completion_tokens"}
    }
)
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/Nayjest/lm-proxy-db-connector.git
cd lm-proxy-db-connector

# Install in development mode
pip install -e .
```

### Running Tests

```bash
# Start test databases (PostgreSQL and MySQL)
docker compose up -d

# Run tests
pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
