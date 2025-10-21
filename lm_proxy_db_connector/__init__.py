"""
lm_proxy_db_connector - Minimalistic database connector for LM Proxy
"""

from typing import Optional

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, Session


_engine: Optional[Engine] = None
_SessionFactory: Optional[scoped_session[Session]] = None


class Component:
    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError(
                "Database connection string is missing in the DB component configuration."
            )
        _init_db(dsn)


def _init_db(connection_string: str):
    global _engine, _SessionFactory
    if _engine is None:
        _engine = create_engine(connection_string, pool_pre_ping=True)
        _SessionFactory = scoped_session(sessionmaker(bind=_engine))


def db_session() -> Session:
    """
    Facade for obtaining the current SQLAlchemy session.
    :return:
    """
    if _SessionFactory is None:
        raise RuntimeError("Database engine is not initialized. Call init_db() first.")
    return _SessionFactory()


def db_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialized. Call init_db() first.")
    return _engine
