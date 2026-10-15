import os
import unittest
import wave
from io import BytesIO
from unittest.mock import Mock, patch
from xml.etree import ElementTree

from app.services.cap import CAP_NAMESPACE, generate_cap_xml
from app.services.speech import transcribe_audio
from app.services.triage import analyze_transcript


class TriageTests(unittest.TestCase):
    def test_partial_azure_configuration_fails_instead_of_using_mock(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AZURE_OPENAI_ENDPOINT": "https://example.invalid",
                "AZURE_OPENAI_KEY": "",
                "AZURE_OPENAI_DEPLOYMENT_NAME": "",
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "Configure AZURE_OPENAI"):
                analyze_transcript("Fire near campus")

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

    def test_critical_medical_demo_counts_passengers_and_overrides_safety(self) -> None:
        with patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "", "AZURE_OPENAI_KEY": "", "AZURE_OPENAI_DEPLOYMENT_NAME": ""}):
            result = analyze_transcript(
                "Emergency at SRM Tech Park! Car crash with 2 passengers unconscious and heavy bleeding!"
            )

        self.assertEqual(result.incident_type, "Medical")
        self.assertEqual(result.casualty_count, 2)
        self.assertEqual(result.urgency_rating, 5)
        self.assertEqual(result.cap_severity, "Extreme")
        self.assertEqual(result.extracted_location_name, "SRM Tech Park")

    def test_fire_demo_is_critical(self) -> None:
        with patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "", "AZURE_OPENAI_KEY": "", "AZURE_OPENAI_DEPLOYMENT_NAME": ""}):
            result = analyze_transcript(
                "Electrical short circuit and fire outburst near Java Canteen! Building evacuation required!"
            )

        self.assertEqual(result.incident_type, "Fire")
        self.assertEqual(result.urgency_rating, 5)
        self.assertEqual(result.cap_severity, "Extreme")
        self.assertEqual(result.extracted_location_name, "Java Canteen")

    def test_non_urgent_demo_does_not_treat_negated_injuries_as_positive(self) -> None:
        with patch.dict(os.environ, {"AZURE_OPENAI_ENDPOINT": "", "AZURE_OPENAI_KEY": "", "AZURE_OPENAI_DEPLOYMENT_NAME": ""}):
            result = analyze_transcript(
                "Minor water pipe leak near Hostel Block 3. No injuries."
            )

        self.assertEqual(result.urgency_rating, 2)
        self.assertEqual(result.casualty_count, 0)
        self.assertEqual(result.cap_severity, "Minor")
        self.assertEqual(result.extracted_location_name, "Hostel Block 3")


class SpeechTests(unittest.TestCase):
    def test_audio_fallback_without_credentials(self) -> None:
        with patch.dict(os.environ, {"AZURE_SPEECH_KEY": "", "AZURE_SPEECH_REGION": ""}):
            self.assertIn("Audio received", transcribe_audio(b""))

    def test_empty_audio_with_credentials_is_rejected(self) -> None:
        with patch.dict(
            os.environ,
            {"AZURE_SPEECH_KEY": "configured", "AZURE_SPEECH_REGION": "region"},
        ):
            with self.assertRaisesRegex(ValueError, "audio file is empty"):
                transcribe_audio(b"")

    def test_partial_speech_configuration_fails_explicitly(self) -> None:
        with patch.dict(
            os.environ,
            {"AZURE_SPEECH_KEY": "configured", "AZURE_SPEECH_REGION": ""},
        ):
            with self.assertRaisesRegex(RuntimeError, "Both AZURE_SPEECH_KEY"):
                transcribe_audio(b"")

    def test_invalid_audio_is_rejected_when_speech_is_configured(self) -> None:
        with patch.dict(
            os.environ,
            {"AZURE_SPEECH_KEY": "configured", "AZURE_SPEECH_REGION": "region"},
        ):
            with self.assertRaisesRegex(ValueError, "valid WAV"):
                transcribe_audio(b"not a WAV file")

    def test_wav_pcm_is_sent_to_azure_speech_stream(self) -> None:
        wav_bytes = BytesIO()
        with wave.open(wav_bytes, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            pcm_audio = b"\x01\x00\x02\x00"
            wav_file.writeframes(pcm_audio)

        import azure.cognitiveservices.speech as speechsdk

        stream = Mock()
        recognition_result = Mock(
            reason=speechsdk.ResultReason.RecognizedSpeech,
            text="Medical emergency at campus.",
        )
        with (
            patch.dict(
                os.environ,
                {"AZURE_SPEECH_KEY": "configured", "AZURE_SPEECH_REGION": "region"},
            ),
            patch.object(speechsdk.audio, "PushAudioInputStream", return_value=stream),
            patch.object(speechsdk, "SpeechConfig"),
            patch.object(speechsdk.audio, "AudioStreamFormat") as audio_format,
            patch.object(speechsdk.audio, "AudioConfig"),
            patch.object(
                speechsdk,
                "SpeechRecognizer",
                return_value=Mock(recognize_once=Mock(return_value=recognition_result)),
            ),
        ):
            transcript = transcribe_audio(wav_bytes.getvalue())

        self.assertEqual(transcript, "Medical emergency at campus.")
        self.assertEqual(audio_format.call_args.kwargs["samples_per_second"], 16000)
        stream.write.assert_called_once_with(pcm_audio)
        stream.close.assert_called_once_with()


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
