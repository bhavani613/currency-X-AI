"""Shared SQLAlchemy declarative base.

Importing :data:`Base` in your model modules ensures they are registered
on the *same* metadata object, so ``Base.metadata.create_all`` can find
them.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()