"""Opt-in compact project lists; omitted campaigns mean not requested, not empty.

Keep the public full response as the default. Compact mode never touches the
Campaign relationship, even during Pydantic serialization, and retains every
other response field/validator. Do not mutate ORM relationships to fake [].
"""
from fastapi.responses import JSONResponse
from sqlalchemy.orm import selectinload

from core import models, schemas


CAMPAIGNS = {'integrations': {'__all__': {'campaigns'}}}


def list_options(include_campaigns):
    integrations = selectinload(models.Client.integrations)
    if include_campaigns:
        return integrations.selectinload(models.Integration.campaigns)
    return integrations.raiseload(models.Integration.campaigns)


def _attributes(row, schema, excluded):
    missing = object()
    values = {}
    for name in schema.model_fields:
        if name in excluded:
            continue
        value = getattr(row, name, missing)
        if value is not missing:
            values[name] = value
    return values


def project_response(row, include_campaigns=True):
    if include_campaigns:
        return schemas.ClientResponse.model_validate(row)
    values = _attributes(row, schemas.ClientResponse, {'integrations'})
    values['integrations'] = [
        _attributes(item, schemas.IntegrationResponse, {'campaigns', 'access_token'})
        for item in row.integrations
    ]
    return schemas.ClientResponse.model_validate(values)


def compact_projects(rows):
    # A pre-serialized Response prevents FastAPI from reintroducing the optional
    # campaigns default. Absence is explicit; integrations/settings stay intact.
    return JSONResponse([project_response(row, False).model_dump(mode='json', exclude=CAMPAIGNS)
                         for row in rows])


def compact_tree(tree):
    return JSONResponse(tree.model_dump(mode='json', exclude={
        'root_projects': {'__all__': CAMPAIGNS},
        'folders': {'__all__': {'projects': {'__all__': CAMPAIGNS}}},
    }))
