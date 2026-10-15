import json
import os
import re
from typing import Literal

from openai import AzureOpenAI
from pydantic import BaseModel, Field

CAMPUS_LATITUDE = 12.8231
CAMPUS_LONGITUDE = 80.0444


class TriageResult(BaseModel):
    incident_type: Literal["Medical", "Fire", "Structural Collapse", "Police"]
    urgency_rating: int = Field(ge=1, le=5)
    casualty_count: int = Field(ge=0)
    extracted_location_name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    cap_severity: Literal["Extreme", "Severe", "Moderate", "Minor"]


def _mock_analysis(text: str) -> TriageResult:
    lower_text = text.casefold()
    incident_type: Literal["Medical", "Fire", "Structural Collapse", "Police"] = "Medical"
    if any(word in lower_text for word in ("fire", "smoke", "electrical short", "explosion")):
        incident_type = "Fire"
    elif any(word in lower_text for word in ("collapse", "collapsed", "building fell", "trapped")):
        incident_type = "Structural Collapse"
    elif any(word in lower_text for word in ("assault", "robbery", "police", "threat")):
        incident_type = "Police"

    casualty_match = re.search(
        r"\b(\d+|one|two|three|four|five)\s+(?:people|person|passengers?|victims?|injured)\b",
        lower_text,
    )
    casualty_count = 0
    if casualty_match:
        count = casualty_match.group(1)
        casualty_count = int(count) if count.isdigit() else {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
        }[count]
    urgency = 4 if any(word in lower_text for word in ("emergency", "crash", "injur", "evacuation")) else 2
    severity: Literal["Extreme", "Severe", "Moderate", "Minor"] = "Severe" if urgency >= 4 else "Moderate"
    location = next(
        (name for name in ("SRM Tech Park", "Java Canteen", "Hostel Block 3", "SRMIST Kattankulathur") if name.casefold() in lower_text),
        "SRM Institute of Science and Technology, Kattankulathur",
    )
    return TriageResult(
        incident_type=incident_type,
        urgency_rating=urgency,
        casualty_count=casualty_count,
        extracted_location_name=location,
        latitude=CAMPUS_LATITUDE,
        longitude=CAMPUS_LONGITUDE,
        cap_severity=severity,
    )


def analyze_transcript(text: str) -> TriageResult:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    if endpoint and api_key and deployment:
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
        )
        completion = client.chat.completions.create(
            model=deployment,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Triage emergency reports. Return JSON with incident_type (Medical, Fire, "
                        "Structural Collapse, or Police), urgency_rating (1-5), casualty_count, "
                        "extracted_location_name, latitude, longitude, and cap_severity "
                        "(Extreme, Severe, Moderate, or Minor). Use coordinates near SRMIST "
                        "Kattankulathur (12.8231, 80.0444) when the location is unclear."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("Azure OpenAI returned an empty triage response.")
        result = TriageResult.model_validate(json.loads(content))
    else:
        result = _mock_analysis(text)

    if any(keyword in text.casefold() for keyword in ("unconscious", "bleeding", "trapped", "fire", "explosion")):
        result = result.model_copy(update={"urgency_rating": 5, "cap_severity": "Extreme"})
    return result
