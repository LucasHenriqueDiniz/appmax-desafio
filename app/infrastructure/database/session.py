from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)

# expire_on_commit=False: os objetos continuam legiveis apos o commit,
# necessario para montar a resposta HTTP depois da transacao fechar
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False)
