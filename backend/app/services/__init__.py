# ============================================================
# Lentis Gallery — Services Package
# ------------------------------------------------------------
# "services" holds the business logic layer. Endpoints (in api/)
# are thin — they parse the request, call a service function, and
# return the result. Services contain the actual rules (e.g. how
# login works, how refresh rotation works). This separation keeps
# routes readable and makes logic easy to test independently.
# ============================================================
