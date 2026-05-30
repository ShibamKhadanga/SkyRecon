from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Reconnect on stale connections
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,      # Log SQL in debug mode
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency – yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_database_if_not_exists():
    """Checks if the configured database exists and creates it if it doesn't."""
    from sqlalchemy.engine.url import make_url
    try:
        url = make_url(settings.DATABASE_URL)
        db_name = url.database
        
        # Connect to default 'postgres' database to check/create target db
        maintenance_url = url.set(database="postgres")
        temp_engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
        
        with temp_engine.connect() as conn:
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = :dbname"), {"dbname": db_name})
            exists = result.scalar()
            
            if not exists:
                print(f"[DB] Target database '{db_name}' does not exist. Creating it now...")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
                print(f"[DB] Target database '{db_name}' created successfully.")
            else:
                print(f"[DB] Target database '{db_name}' already exists.")
        temp_engine.dispose()
    except Exception as e:
        print(f"[DB] Warning: Could not automatically verify or create database: {e}")


def init_db():
    """Create all tables and install PL/pgSQL stored procedures."""
    _create_database_if_not_exists()
    Base.metadata.create_all(bind=engine)

    # Add progress_pct column if upgrading from older schema (idempotent)
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE analyses ADD COLUMN IF NOT EXISTS progress_pct INTEGER DEFAULT 0
        """))
        conn.commit()

    _install_stored_procedures()
    from .core.seeder import seed_mock_data_if_empty
    db = SessionLocal()
    try:
        seed_mock_data_if_empty(db)
    finally:
        db.close()


def _install_stored_procedures():
    """Execute the PL/pgSQL procedure definitions against the live database."""
    import os
    sql_path = os.path.join(os.path.dirname(__file__), "..", "sql", "procedures.sql")
    sql_path = os.path.abspath(sql_path)
    if not os.path.exists(sql_path):
        return  # Skip if file not present (first boot before sql/ is created)
    with engine.connect() as conn:
        with open(sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
        conn.execute(text(sql))
        # Seed default categories using the newly installed stored procedure
        conn.execute(text("SELECT seed_default_categories();"))
        conn.commit()
