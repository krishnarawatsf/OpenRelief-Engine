from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

CAP_NAMESPACE = "urn:oasis:names:tc:emergency:cap:1.2"
register_namespace("", CAP_NAMESPACE)

CAP_CATEGORY = {
    "Medical": "Health",
    "Fire": "Fire",
    "Structural Collapse": "Rescue",
    "Police": "Security",
}


def _tag(parent: Element, name: str, text: str) -> Element:
    element = SubElement(parent, f"{{{CAP_NAMESPACE}}}{name}")
    element.text = text
    return element


def generate_cap_xml(incident_data: dict[str, Any]) -> str:
    sent = incident_data.get("created_at") or datetime.now(timezone.utc)
    if isinstance(sent, str):
        sent = datetime.fromisoformat(sent.replace("Z", "+00:00"))
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    sent_text = sent.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    expires = (sent + timedelta(hours=1)).astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    incident_type = str(incident_data.get("incident_type", "Emergency"))
    urgency_rating = int(incident_data.get("urgency_rating", 3))
    cap_severity = str(incident_data.get("cap_severity", "Moderate"))

    alert = Element(f"{{{CAP_NAMESPACE}}}alert")
    _tag(alert, "identifier", str(incident_data.get("id") or uuid4()))
    _tag(alert, "sender", "openrelief-engine")
    _tag(alert, "sent", sent_text)
    _tag(alert, "status", "Actual")
    _tag(alert, "msgType", "Alert")
    _tag(alert, "scope", "Public")

    info = SubElement(alert, f"{{{CAP_NAMESPACE}}}info")
    _tag(info, "category", CAP_CATEGORY.get(incident_type, "Other"))
    _tag(info, "event", incident_type)
    _tag(info, "urgency", "Immediate" if urgency_rating >= 5 else "Expected" if urgency_rating >= 3 else "Future")
    _tag(info, "severity", cap_severity)
    _tag(info, "certainty", "Observed")
    _tag(info, "effective", sent_text)
    _tag(info, "expires", expires)
    _tag(info, "senderName", "OpenRelief Emergency Response")
    _tag(info, "headline", f"{incident_type} emergency - {cap_severity}")
    description = str(incident_data.get("transcript", incident_type))
    _tag(info, "description", description)
    _tag(info, "instruction", "Follow instructions from local emergency services.")
    area = SubElement(info, f"{{{CAP_NAMESPACE}}}area")
    _tag(area, "areaDesc", str(incident_data.get("extracted_location_name", "SRMIST Kattankulathur")))
    circle = SubElement(area, f"{{{CAP_NAMESPACE}}}circle")
    circle.text = (
        f"{float(incident_data.get('latitude', 12.8231))},"
        f"{float(incident_data.get('longitude', 80.0444))} 1"
    )
    return tostring(alert, encoding="unicode", xml_declaration=True)
