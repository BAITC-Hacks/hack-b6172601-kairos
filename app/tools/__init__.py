"""Importing this package registers every tool with the agent registry.

IMPORTANT: a new tool module is invisible until it is imported here. Adding
app/tools/refunds.py alone does nothing - the tool simply never appears in
REGISTRY, in /api/tools or in the schemas sent to the model, and the only
symptom is that the agent never calls it. Add the import below.
"""
from app.tools import finance  # noqa: F401
