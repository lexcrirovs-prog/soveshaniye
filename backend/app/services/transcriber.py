import logging
import tempfile
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def get_whisper_model():
    """Lazy-load the Whisper model (singleton)."""
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


def transcribe(audio_data: bytes) -> Optional[dict]:
    """
    Transcribe audio data using faster-whisper.

    Returns:
        dict with keys: text, segments, confidence, language
    """
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
            logger.error("Transcription failed: %s", e)
            return None
