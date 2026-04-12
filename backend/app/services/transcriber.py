import logging
import tempfile
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def get_whisper_model():
    """Lazy-load the local Whisper model (singleton)."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        logger.info(
            "Loading Whisper model: %s (device=%s, compute_type=%s)",
            settings.whisper_model,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        logger.info("Whisper model loaded successfully")
    return _model


def _transcribe_local(audio_data: bytes) -> Optional[dict]:
    """Transcribe using local faster-whisper model."""
    model = get_whisper_model()

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
        tmp.write(audio_data)
        tmp.flush()

        try:
            segments_gen, info = model.transcribe(
                tmp.name,
                language="ru",
                beam_size=5,
                best_of=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )

            segments = []
            full_text_parts = []
            total_confidence = 0.0
            count = 0

            for segment in segments_gen:
                seg_data = {
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "text": segment.text.strip(),
                    "confidence": round(segment.avg_log_prob, 4) if segment.avg_log_prob else None,
                }
                segments.append(seg_data)
                full_text_parts.append(segment.text.strip())
                if segment.avg_log_prob:
                    total_confidence += segment.avg_log_prob
                    count += 1

            full_text = " ".join(full_text_parts)
            avg_confidence = round(total_confidence / count, 4) if count > 0 else None

            return {
                "text": full_text,
                "segments": segments,
                "confidence": avg_confidence,
                "language": info.language if info else "ru",
            }

        except Exception as e:
            logger.error("Local transcription failed: %s", e)
            return None


def _transcribe_openai(audio_data: bytes) -> Optional[dict]:
    """Transcribe using OpenAI Whisper API (whisper-1)."""
    from openai import OpenAI

    if not settings.openai_api_key:
        logger.error("OPENAI_API_KEY not set, cannot use OpenAI Whisper")
        return None

    client = OpenAI(api_key=settings.openai_api_key)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
        tmp.write(audio_data)
        tmp.flush()
        tmp.seek(0)

        try:
            # Get verbose transcription with timestamps
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=open(tmp.name, "rb"),
                language="ru",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )

            segments = []
            if hasattr(result, "segments") and result.segments:
                for seg in result.segments:
                    segments.append({
                        "start": round(seg["start"], 2) if isinstance(seg, dict) else round(seg.start, 2),
                        "end": round(seg["end"], 2) if isinstance(seg, dict) else round(seg.end, 2),
                        "text": (seg["text"] if isinstance(seg, dict) else seg.text).strip(),
                        "confidence": None,
                    })

            text = result.text if hasattr(result, "text") else str(result)

            return {
                "text": text.strip(),
                "segments": segments,
                "confidence": None,
                "language": "ru",
            }

        except Exception as e:
            logger.error("OpenAI Whisper transcription failed: %s", e)
            return None


def transcribe(audio_data: bytes) -> Optional[dict]:
    """
    Transcribe audio data using configured provider.

    Provider is set via WHISPER_PROVIDER env var:
    - "openai" — OpenAI Whisper API (fast, cloud, uses OPENAI_API_KEY)
    - "local"  — faster-whisper (local, slow on CPU, no API key needed)
    """
    provider = settings.whisper_provider.lower()

    if provider == "openai":
        logger.info("Transcribing via OpenAI Whisper API")
        return _transcribe_openai(audio_data)
    else:
        logger.info("Transcribing via local faster-whisper")
        return _transcribe_local(audio_data)
