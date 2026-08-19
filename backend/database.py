from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings

# ===== 时区统一：Asia/Shanghai (UTC+8) =====
# 阿里云 ECS 上的 MySQL system_time_zone 是 UTC。
# 解决方案：对每一条新拿到的连接立即执行 SET SESSION time_zone = '+08:00'，
# 把「当前会话读写 DATETIME 的语境」统一锁死为东八区，避免受 OS / MySQL 设置影响。
TZ_OFFSET = "+08:00"

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    future=True,
)


@event.listens_for(engine, "connect")
def _set_mysql_timezone(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"SET SESSION time_zone = '{TZ_OFFSET}'")
    finally:
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
