import getpass

from sqlalchemy import select

from .database import Base, SessionLocal, engine
from .models import User
from .security import passwords


def main():
    Base.metadata.create_all(engine)
    name = input("Nome do administrador: ").strip()
    email = input("E-mail: ").strip().lower()
    password = getpass.getpass("Senha (mínimo 10 caracteres): ")
    if len(name) < 2 or "@" not in email or len(password) < 10:
        raise SystemExit("Dados inválidos.")
    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("E-mail já cadastrado.")
        db.add(User(name=name, email=email, role="admin", password_hash=passwords.hash(password)))
        db.commit()
    print("Administrador criado.")


if __name__ == "__main__":
    main()
