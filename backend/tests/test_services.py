import os
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from app.services.cap import CAP_NAMESPACE, generate_cap_xml
from app.services.triage import analyze_transcript


class TriageTests(unittest.TestCase):
    def test_safety_keywords_override_urgency_and_severity(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "",
                "AZURE_OPENAI_KEY": "",
                "AZURE_OPENAI_DEPLOYMENT_NAME": "",
            },
        ):
            result = analyze_transcript("Minor issue, one person is unconscious near SRM Tech Park.")

        self.assertEqual(result.urgency_rating, 5)
        self.assertEqual(result.cap_severity, "Extreme")
        self.assertEqual(result.casualty_count, 1)


class CapExportTests(unittest.TestCase):
    def test_cap_export_contains_required_fields_and_escapes_transcript(self) -> None:
        xml = generate_cap_xml(
            {
                "id": "incident-1",
                "incident_type": "Medical",
                "urgency_rating": 5,
                "cap_severity": "Extreme",
                "transcript": "Injury & smoke <reported>",
                "latitude": 12.8231,
                "longitude": 80.0444,
            }
        )
        root = ElementTree.fromstring(xml)
        namespace = {"cap": CAP_NAMESPACE}

        self.assertEqual(root.findtext("cap:msgType", namespaces=namespace), "Alert")
        self.assertEqual(root.findtext("cap:info/cap:urgency", namespaces=namespace), "Immediate")
        self.assertEqual(root.findtext("cap:info/cap:severity", namespaces=namespace), "Extreme")
        self.assertEqual(
            root.findtext("cap:info/cap:description", namespaces=namespace),
            "Injury & smoke <reported>",
        )
        self.assertIsNotNone(root.find("cap:info/cap:area/cap:circle", namespace))


if __name__ == "__main__":
    unittest.main()
