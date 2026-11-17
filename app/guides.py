"""All services. Each service lives in its own module; see app/fields.py for the field schema."""
from .guide_lpa import LPA_HEALTH, LPA_PROPERTY
from .guide_probate import PROBATE
from .guide_will import WILL

SERVICES = {s["id"]: s for s in (WILL, LPA_PROPERTY, LPA_HEALTH, PROBATE)}
