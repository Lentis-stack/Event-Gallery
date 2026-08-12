# ============================================================
# Lentis Gallery — Schemas Package
# ------------------------------------------------------------
# "schemas" holds Pydantic models used for API request/response
# validation. Pydantic schemas are SEPARATE from SQLAlchemy ORM
# models: a schema defines what data crosses the API boundary, so
# we never accidentally leak internal DB fields (like a password
# hash) to the frontend.
# ============================================================
