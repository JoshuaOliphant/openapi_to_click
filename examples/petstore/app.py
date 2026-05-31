"""A tiny real FastAPI app used by the integration test.

It serves a handful of routes that exercise the generator end to end: a GET
with a path parameter and an optional query, an authenticated GET, a POST with
a JSON body deserialized into a model, and a path that returns a 404 error.

FastAPI generates its own OpenAPI spec at ``/openapi.json``, so the integration
test generates the CLI from the *running* app's spec — there is no separate spec
file to drift out of sync with these handlers.

Run standalone with::

    uvicorn examples.petstore.app:app --port 8000
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

app = FastAPI(
    title="Petstore Example",
    version="1.0.0",
    servers=[{"url": "http://127.0.0.1:8000"}],
)

# A trivial in-memory store so POST results are observable on later GETs.
_PETS: dict[int, dict] = {1: {"id": 1, "name": "Rex", "tag": "dog"}}

# Declaring an HTTP bearer scheme makes it a `securityScheme` in the generated
# OpenAPI spec, which is what tells openapi-python-client to honour the client's
# bearer token — and therefore what the CLI's `--token` flag drives.
bearer = HTTPBearer()


class NewPet(BaseModel):
    name: str
    tag: str | None = None


class Pet(BaseModel):
    id: int
    name: str
    tag: str | None = None


@app.get("/pets/{pet_id}", operation_id="get_pet", tags=["pets"])
def get_pet(pet_id: int, detail: bool = False) -> Pet:
    """Fetch a single pet by id."""
    pet = _PETS.get(pet_id)
    if pet is None:
        raise HTTPException(status_code=404, detail="Pet not found")
    return Pet(**pet)


@app.post("/pets", operation_id="create_pet", tags=["pets"], status_code=201)
def create_pet(body: NewPet) -> Pet:
    """Create a pet from a JSON body."""
    new_id = max(_PETS) + 1 if _PETS else 1
    record = {"id": new_id, "name": body.name, "tag": body.tag}
    _PETS[new_id] = record
    return Pet(**record)


@app.get("/me", operation_id="whoami", tags=["auth"])
def whoami(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict[str, str]:
    """Echo back the bearer token, proving auth headers reach the server."""
    return {"token": credentials.credentials}
