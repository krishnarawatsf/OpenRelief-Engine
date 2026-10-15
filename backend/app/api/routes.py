import json
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from openai import APIError
from pydantic import BaseModel, Field, ValidationError

from app.database import require_pool
from app.services.cap import generate_cap_xml
from app.services.spatial import find_nearest_responder
from app.services.speech import transcribe_audio
from app.services.triage import analyze_transcript

router = APIRouter(prefix="/api")

UNIT_BY_INCIDENT = {
    "Medical": "AMBULANCE",
    "Fire": "FIRE_TRUCK",
    "Structural Collapse": "FIRE_TRUCK",
    "Police": "POLICE",
}


class TextTriageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)


class IncidentResolution(BaseModel):
    status: str = Field(pattern="^(RESOLVED|CANCELLED)$")


def _public_incident(row: Any) -> dict[str, Any]:
    incident = dict(row)
    incident["id"] = str(incident["id"])
    if incident.get("assigned_responder_id") is not None:
        incident["assigned_responder_id"] = str(incident["assigned_responder_id"])
    for field in ("location",):
        incident.pop(field, None)
    incident["latitude"] = incident.pop("lat", None)
    incident["longitude"] = incident.pop("lon", None)
    if incident.get("responder_id") is not None:
        incident["assigned_responder"] = {
            "id": str(incident.pop("responder_id")),
            "unit_name": incident.pop("responder_unit_name"),
            "unit_type": incident.pop("responder_unit_type"),
            "latitude": incident.pop("responder_lat"),
            "longitude": incident.pop("responder_lon"),
        }
    else:
        for key in (
            "responder_id",
            "responder_unit_name",
            "responder_unit_type",
            "responder_lat",
            "responder_lon",
        ):
            incident.pop(key, None)
        incident["assigned_responder"] = None
    return incident


@router.post("/triage")
async def triage(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("audio")
        if upload is None or not hasattr(upload, "read"):
            raise HTTPException(status_code=422, detail="Upload an audio file in the 'audio' field.")
        try:
            transcript = await run_in_threadpool(transcribe_audio, await upload.read())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail="Speech recognition provider failed.") from exc
    elif content_type.startswith("application/json"):
        try:
            payload = TextTriageRequest.model_validate(await request.json())
        except (ValidationError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail="Request body must include a non-empty 'text' string.") from exc
        transcript = payload.text.strip()
        if not transcript:
            raise HTTPException(status_code=422, detail="Text must not be empty.")
    else:
        raise HTTPException(status_code=415, detail="Send JSON text or multipart form data with an audio field.")

    try:
        analysis = await run_in_threadpool(analyze_transcript, transcript)
    except (APIError, ValidationError, json.JSONDecodeError, RuntimeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Triage provider failed to return a valid result.",
        ) from exc
    pool = require_pool()
    incident_id = uuid4()
    unit_type = UNIT_BY_INCIDENT[analysis.incident_type]

    async with pool.acquire() as connection:
        async with connection.transaction():
            responder = await find_nearest_responder(
                connection, analysis.latitude, analysis.longitude, unit_type
            )
            priority_score = float(
                analysis.urgency_rating * 20 + min(max(analysis.casualty_count, 0), 20)
            )
            status = "OPEN"
            responder_id = None
            if responder:
                responder_id = responder["id"]
                status = "DISPATCHED"
                await connection.execute(
                    "UPDATE responders SET is_available = FALSE, updated_at = NOW() WHERE id = $1",
                    responder_id,
                )
            row = await connection.fetchrow(
                """
                INSERT INTO incidents (
                    id, transcript, incident_type, extracted_location_name, urgency_rating, casualty_count,
                    priority_score, cap_severity, location, assigned_responder_id, status
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8,
                    ST_SetSRID(ST_MakePoint($9, $10), 4326)::geography, $11, $12
                )
                RETURNING id, transcript, incident_type, extracted_location_name,
                    urgency_rating, casualty_count,
                    priority_score, cap_severity, assigned_responder_id, status, created_at,
                    ST_Y(location::geometry) AS lat, ST_X(location::geometry) AS lon
                """,
                incident_id,
                transcript,
                analysis.incident_type,
                analysis.extracted_location_name,
                analysis.urgency_rating,
                analysis.casualty_count,
                priority_score,
                analysis.cap_severity,
                analysis.longitude,
                analysis.latitude,
                responder_id,
                status,
            )

    incident = _public_incident(row)
    if responder:
        incident["assigned_responder"] = {
            "id": str(responder["id"]),
            "unit_name": responder["unit_name"],
            "unit_type": responder["unit_type"],
            "latitude": responder["lat"],
            "longitude": responder["lon"],
            "distance_km": responder["distance_km"],
        }
    return {
        "transcript": transcript,
        "triage": analysis.model_dump(),
        "incident": incident,
        "assigned_responder": incident["assigned_responder"],
    }


@router.get("/responders")
async def list_responders() -> list[dict[str, Any]]:
    pool = require_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT id, unit_name, unit_type, is_available, updated_at,
                ST_Y(location::geometry) AS latitude, ST_X(location::geometry) AS longitude
            FROM responders
            ORDER BY unit_type, unit_name
            """
        )
    return [
        {
            **dict(row),
            "id": str(row["id"]),
        }
        for row in rows
    ]


@router.get("/incidents")
async def list_incidents() -> list[dict[str, Any]]:
    pool = require_pool()
    async with pool.acquire() as connection:
        rows = await connection.fetch(
            """
            SELECT i.id, i.transcript, i.incident_type, i.extracted_location_name,
                i.urgency_rating, i.casualty_count,
                i.priority_score, i.cap_severity, i.assigned_responder_id, i.status,
                i.created_at, ST_Y(i.location::geometry) AS lat, ST_X(i.location::geometry) AS lon,
                r.id AS responder_id, r.unit_name AS responder_unit_name,
                r.unit_type AS responder_unit_type,
                ST_Y(r.location::geometry) AS responder_lat,
                ST_X(r.location::geometry) AS responder_lon
            FROM incidents i
            LEFT JOIN responders r ON r.id = i.assigned_responder_id
            WHERE i.status IN ('OPEN', 'DISPATCHED')
            ORDER BY i.priority_score DESC, i.created_at DESC
            """
        )
    return [_public_incident(row) for row in rows]


@router.patch("/incidents/{incident_id}/status")
async def update_incident_status(
    incident_id: UUID, update: IncidentResolution
) -> dict[str, str]:
    pool = require_pool()
    async with pool.acquire() as connection:
        async with connection.transaction():
            row = await connection.fetchrow(
                """
                UPDATE incidents
                SET status = $2
                WHERE id = $1 AND status IN ('OPEN', 'DISPATCHED')
                RETURNING assigned_responder_id
                """,
                incident_id,
                update.status,
            )
            if row is None:
                exists = await connection.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM incidents WHERE id = $1)",
                    incident_id,
                )
                if not exists:
                    raise HTTPException(status_code=404, detail="Incident not found.")
                raise HTTPException(status_code=409, detail="Incident is no longer active.")
            responder_id = row["assigned_responder_id"]
            if responder_id is not None:
                await connection.execute(
                    """
                    UPDATE responders SET is_available = TRUE, updated_at = NOW()
                    WHERE id = $1
                    """,
                    responder_id,
                )
    return {"id": str(incident_id), "status": update.status}


@router.get("/incidents/{incident_id}/cap.xml")
async def incident_cap(incident_id: UUID) -> Response:
    pool = require_pool()
    async with pool.acquire() as connection:
        row = await connection.fetchrow(
            """
            SELECT id, transcript, incident_type, extracted_location_name,
                urgency_rating, casualty_count,
                cap_severity, status, created_at,
                ST_Y(location::geometry) AS latitude, ST_X(location::geometry) AS longitude
            FROM incidents WHERE id = $1
            """,
            incident_id,
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return Response(
        content=generate_cap_xml(dict(row)),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="alert_{incident_id}_CAP_v1.2.xml"'},
    )
