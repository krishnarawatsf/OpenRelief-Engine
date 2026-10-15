from io import BytesIO
import os
import wave


def transcribe_audio(audio_bytes: bytes) -> str:
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key and not speech_region:
        return "Audio received for emergency triage. Please confirm the incident details."
    if not speech_key or not speech_region:
        raise RuntimeError("Both AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be configured.")
    if not audio_bytes:
        raise ValueError("The uploaded audio file is empty.")

    import azure.cognitiveservices.speech as speechsdk

    try:
        with wave.open(BytesIO(audio_bytes), "rb") as wav_file:
            if wav_file.getcomptype() != "NONE" or wav_file.getsampwidth() != 2:
                raise ValueError("Upload a WAV file using uncompressed 16-bit PCM audio.")
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            pcm_audio = wav_file.readframes(wav_file.getnframes())
    except (wave.Error, EOFError) as exc:
        raise ValueError("Upload a valid WAV audio file.") from exc

    config = speechsdk.SpeechConfig(subscription=speech_key, region=speech_region)
    audio_format = speechsdk.audio.AudioStreamFormat(
        samples_per_second=sample_rate,
        bits_per_sample=16,
        channels=channels,
    )
    stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
    audio_config = speechsdk.audio.AudioConfig(stream=stream)
    stream.write(pcm_audio)
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
