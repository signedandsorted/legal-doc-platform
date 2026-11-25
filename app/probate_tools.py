"""Small read-only lookup endpoints used by probate guide steps. Nothing here files or submits
anything for the family; they search official lists and the family acts on the result."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import require_user
from .integrations import bona_vacantia

router = APIRouter(prefix="/api/probate", tags=["probate-tools"])


@router.get("/bona-vacantia")
def bona_vacantia_search(surname: str = Query(..., min_length=2, max_length=80), forename: str = Query("", max_length=80), _user=Depends(require_user)):
    try:
        return bona_vacantia.lookup(surname, forename)
    except bona_vacantia.BonaVacantiaUnavailable as exc:
        raise HTTPException(503, str(exc))
