# ============================================================
# Lentis Gallery — Database Base
# ------------------------------------------------------------
# This defines the BASE class that every database table model
# will inherit from. It is the foundation of SQLAlchemy's ORM.
#
# WHAT IS AN ORM?
#   ORM = Object Relational Mapper. It lets us write Python
#   classes that represent database tables. SQLAlchemy then
#   converts our Python operations into SQL queries for us.
#
#   Example: creating a Python object and "committing" it sends
#   an INSERT statement to PostgreSQL. We never write INSERT/SELECT
#   by hand — SQLAlchemy does it for us.
#
# DeclarativeBase is the modern SQLAlchemy 2.x way to build models.
# ============================================================

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models (database tables)."""

    # This is intentionally empty. It just marks a class as a
    # "model". Each table model we create later will do:
    #
    #     class User(Base):
    #         __tablename__ = "users"
    #         id = mapped_column(...)
    #
    # And SQLAlchemy will know to create/use the "users" table.
    pass
