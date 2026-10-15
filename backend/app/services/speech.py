import os


def transcribe_audio(audio_bytes: bytes) -> str:
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not speech_region:
        return "Audio received for emergency triage. Please confirm the incident details."
    if not audio_bytes:
        raise ValueError("The uploaded audio file is empty.")

    import azure.cognitiveservices.speech as speechsdk

    config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    audio_config = speechsdk.audio.AudioConfig(stream=speechsdk.audio.PushAudioInputStream())
    stream = audio_config.stream
    stream.write(audio_bytes)
    stream.close()
    recognizer = speechsdk.SpeechRecognizer(speech_config=config, audio_config=audio_config)
    result = recognizer.recognize_once()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech and result.text.strip():
        return result.text
    if result.reason == speechsdk.ResultReason.NoMatch:
        raise ValueError("No speech could be recognized from the uploaded audio.")
    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        raise RuntimeError(f"Speech recognition failed: {details.reason}: {details.error_details or ''}")
    raise RuntimeError(f"Speech recognition ended unexpectedly: {result.reason}.")
