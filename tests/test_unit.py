"""
Tests for lm_proxy_db_connector module
"""
import pytest
from sqlalchemy import text
from lm_proxy_db_connector import (
    init_db,
    db,
    is_initialized,
    db_session,
    dispose_db,
    NotInitializedError,
    DbConfig,
    DbComponent,
)


@pytest.fixture(autouse=True)
def cleanup_db():
    """Ensure clean state before and after each test"""
    dispose_db()
    yield
    dispose_db()


@pytest.fixture
def db_url():
    """In-memory SQLite database URL"""
    return "sqlite:///:memory:"


class TestDbConfig:
    """Test DbConfig dataclass"""

    def test_default_values(self, db_url):
        config = DbConfig(db_url=db_url)
        assert config.db_url == db_url
        assert config.engine_kwargs == {"pool_pre_ping": True}
        assert config.session_kwargs == {
            "expire_on_commit": False,
            "autoflush": True,
        }

    def test_custom_kwargs(self, db_url):
        config = DbConfig(
            db_url=db_url,
            engine_kwargs={"echo": True},
            session_kwargs={"autocommit": False},
        )
        assert config.engine_kwargs["pool_pre_ping"] is True
        assert config.engine_kwargs["echo"] is True
        assert config.session_kwargs["expire_on_commit"] is False
        assert config.session_kwargs["autocommit"] is False


class TestDbComponent:
    """Test DbComponent dataclass"""

    def test_initialization(self, db_url):
        config = DbConfig(db_url=db_url)
        component = DbComponent(config=config)
        assert component.engine is not None
        assert component.session_factory is not None
        component.dispose()

    def test_get_session(self, db_url):
        config = DbConfig(db_url=db_url)
        component = DbComponent(config=config)
        session = component.get_session()
        assert session is not None
        session.close()
        component.dispose()

    def test_health_check_success(self, db_url):
        config = DbConfig(db_url=db_url)
        component = DbComponent(config=config)
        assert component.health_check() is True
        component.dispose()


class TestInitDb:
    """Test init_db function"""

    def test_init_db(self, db_url):
        component = init_db(db_url)
        assert component is not None
        assert is_initialized() is True

    def test_init_db_with_kwargs(self, db_url):
        component = init_db(
            db_url,
            engine_kwargs={"echo": True},
            session_kwargs={"autocommit": False},
        )
        assert component is not None

    def test_init_db_already_initialized(self, db_url):
        init_db(db_url)
        with pytest.raises(RuntimeError, match="already initialized"):
            init_db(db_url)


class TestDbFacade:
    """Test db() facade function"""

    def test_db_not_initialized(self):
        with pytest.raises(NotInitializedError):
            db()

    def test_db_initialized(self, db_url):
        component = init_db(db_url)
        assert db() is component


class TestIsInitialized:
    """Test is_initialized function"""

    def test_not_initialized(self):
        assert is_initialized() is False

    def test_initialized(self, db_url):
        init_db(db_url)
        assert is_initialized() is True

    def test_after_dispose(self, db_url):
        init_db(db_url)
        dispose_db()
        assert is_initialized() is False


class TestDbSession:
    """Test db_session context manager"""

    def test_db_session_commit(self, db_url):
        init_db(db_url)
        with db_session() as session:
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_db_session_rollback(self, db_url):
        init_db(db_url)
        with pytest.raises(ValueError):
            with db_session() as session:
                session.execute(text("SELECT 1"))
                raise ValueError("Test error")

    def test_db_session_not_initialized(self):
        with pytest.raises(NotInitializedError):
            with db_session():
                pass


class TestDisposeDb:
    """Test dispose_db function"""

    def test_dispose_db(self, db_url):
        init_db(db_url)
        dispose_db()
        assert is_initialized() is False

    def test_dispose_db_not_initialized(self):
        dispose_db()  # Should not raise
        assert is_initialized() is False

    def test_dispose_db_multiple_times(self, db_url):
        init_db(db_url)
        dispose_db()
        dispose_db()  # Should not raise
        assert is_initialized() is False


class TestThreadSafety:
    """Test thread safety of global state"""

    def test_concurrent_initialization_attempt(self, db_url):
        import threading
        import time

        errors = []

        def try_init():
            try:
                time.sleep(0.01)  # Small delay to increase contention
                init_db(db_url)
            except RuntimeError as e:
                errors.append(e)

        init_db(db_url)
        threads = [threading.Thread(target=try_init) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 3
        assert all("already initialized" in str(e) for e in errors)
