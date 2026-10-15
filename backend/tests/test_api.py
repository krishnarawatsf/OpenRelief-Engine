import os
import unittest
from unittest.mock import AsyncMock, patch
from uuid import UUID

from fastapi import HTTPException

from app.api.routes import IncidentResolution, triage, update_incident_status

RESPONDER_ID = UUID("00000000-0000-4000-8000-000000000001")


class FakeRequest:
    headers = {"content-type": "application/json"}

    def __init__(self, payload: object) -> None:
        self.payload = payload

    async def json(self) -> object:
        return self.payload


class FakeTransaction:
    async def __aenter__(self) -> "FakeTransaction":
        return self

    async def __aexit__(self, *args: object) -> bool:
        return False


class FakeConnection:
    def __init__(self, responder_id: UUID | None = None, exists: bool = True) -> None:
        self.responder_id = responder_id
        self.exists = exists
        self.insert_args: tuple[object, ...] | None = None
        self.executed: list[tuple[object, ...]] = []

    def transaction(self) -> FakeTransaction:
        return FakeTransaction()

    async def execute(self, *args: object) -> None:
        self.executed.append(args)

    async def fetchrow(self, query: str, *args: object) -> dict[str, object]:
        if "INSERT INTO incidents" in query:
            self.insert_args = args
            return {
                "id": args[0],
                "transcript": args[1],
                "incident_type": args[2],
                "extracted_location_name": args[3],
                "urgency_rating": args[4],
                "casualty_count": args[5],
                "priority_score": args[6],
                "cap_severity": args[7],
                "assigned_responder_id": args[10],
                "status": args[11],
                "created_at": None,
                "lat": args[9],
                "lon": args[8],
            }
        return {"assigned_responder_id": self.responder_id}

    async def fetchval(self, query: str, incident_id: UUID) -> bool:
        return self.exists


class FakeAcquire:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(self, *args: object) -> bool:
        return False


class FakePool:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection

    def acquire(self) -> FakeAcquire:
        return FakeAcquire(self.connection)


class TriageRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_triage_dispatches_responder_and_stores_lon_before_lat(self) -> None:
        connection = FakeConnection()
        responder = {
            "id": RESPONDER_ID,
            "unit_name": "SRM Ambulance 1",
            "unit_type": "AMBULANCE",
            "lat": 12.82,
            "lon": 80.04,
            "distance_km": 0.5,
        }
        with (
            patch.dict(
                os.environ,
                {
                    "AZURE_OPENAI_ENDPOINT": "",
                    "AZURE_OPENAI_KEY": "",
                    "AZURE_OPENAI_DEPLOYMENT_NAME": "",
                },
            ),
            patch("app.api.routes.require_pool", return_value=FakePool(connection)),
            patch(
                "app.api.routes.find_nearest_responder",
                new=AsyncMock(return_value=responder),
            ),
        ):
            result = await triage(
                FakeRequest({"text": "Emergency at SRM Tech Park, two passengers unconscious."})
            )

        self.assertEqual(connection.insert_args[8:10], (80.0444, 12.8231))
        self.assertEqual(result["incident"]["status"], "DISPATCHED")
        self.assertEqual(result["assigned_responder"]["unit_name"], "SRM Ambulance 1")
        self.assertEqual(len(connection.executed), 1)

    async def test_triage_keeps_incident_open_when_no_responder_is_available(self) -> None:
        connection = FakeConnection()
        with (
            patch.dict(
                os.environ,
                {
                    "AZURE_OPENAI_ENDPOINT": "",
                    "AZURE_OPENAI_KEY": "",
                    "AZURE_OPENAI_DEPLOYMENT_NAME": "",
                },
            ),
            patch("app.api.routes.require_pool", return_value=FakePool(connection)),
            patch(
                "app.api.routes.find_nearest_responder",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await triage(FakeRequest({"text": "Minor water leak near Hostel Block 3."}))

        self.assertEqual(result["incident"]["status"], "OPEN")
        self.assertIsNone(result["assigned_responder"])
        self.assertEqual(connection.executed, [])

    async def test_triage_rejects_blank_and_unsupported_payloads(self) -> None:
        for request, status_code in (
            (FakeRequest({"text": "  "}), 422),
            (FakeRequest({}), 422),
        ):
            with self.subTest(status_code=status_code), self.assertRaises(HTTPException) as error:
                await triage(request)
            self.assertEqual(error.exception.status_code, status_code)

        request = FakeRequest({})
        request.headers = {"content-type": "text/plain"}
        with self.assertRaises(HTTPException) as error:
            await triage(request)
        self.assertEqual(error.exception.status_code, 415)


class IncidentResolutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolution_releases_assigned_responder(self) -> None:
        connection = FakeConnection(responder_id=RESPONDER_ID)
        with patch("app.api.routes.require_pool", return_value=FakePool(connection)):
            result = await update_incident_status(
                UUID("00000000-0000-4000-8000-000000000002"),
                IncidentResolution(status="RESOLVED"),
            )

        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(len(connection.executed), 1)
        self.assertEqual(connection.executed[0][-1], RESPONDER_ID)

    async def test_resolution_distinguishes_missing_incident(self) -> None:
        connection = FakeConnection(exists=False)
        connection.fetchrow = AsyncMock(return_value=None)
        with patch("app.api.routes.require_pool", return_value=FakePool(connection)):
            with self.assertRaises(HTTPException) as error:
                await update_incident_status(
                    UUID("00000000-0000-4000-8000-000000000002"),
                    IncidentResolution(status="CANCELLED"),
                )

        self.assertEqual(error.exception.status_code, 404)

    async def test_resolution_rejects_already_inactive_incident(self) -> None:
        connection = FakeConnection(responder_id=None)
        connection.fetchrow = AsyncMock(return_value=None)
        connection.fetchval = AsyncMock(return_value=True)
        with patch("app.api.routes.require_pool", return_value=FakePool(connection)):
            with self.assertRaises(HTTPException) as error:
                await update_incident_status(
                    UUID("00000000-0000-4000-8000-000000000002"),
                    IncidentResolution(status="RESOLVED"),
                )

        self.assertEqual(error.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
