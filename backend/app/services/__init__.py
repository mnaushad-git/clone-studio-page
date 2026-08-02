"""Service layer — business logic that composes repository calls into transactions.
Never contains raw SQLAlchemy queries directly (those live in app/repositories/).
"""

from __future__ import annotations
