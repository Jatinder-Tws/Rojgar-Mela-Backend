"""Gemini Live API proxy — strict audio-to-audio and text-to-voice."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

# Monkeypatch websockets to disable client-initiated pings and timeouts.
# This prevents "sent 1011 (internal error) keepalive ping timeout" when Google's
# servers do not respond to client WebSocket ping frames.
try:
    import websockets.client
    _orig_client_connect = websockets.client.connect
    def patched_client_connect(*args, **kwargs):
        kwargs['ping_interval'] = None
        kwargs['ping_timeout'] = None
        return _orig_client_connect(*args, **kwargs)
    websockets.client.connect = patched_client_connect
    websockets.connect = patched_client_connect
except Exception:
    pass

try:
    import websockets.asyncio.client
    _orig_asyncio_connect = websockets.asyncio.client.connect
    def patched_asyncio_connect(*args, **kwargs):
        kwargs['ping_interval'] = None
        kwargs['ping_timeout'] = None
        return _orig_asyncio_connect(*args, **kwargs)
    websockets.asyncio.client.connect = patched_asyncio_connect
except Exception:
    pass

from google import genai
from google.genai import types

from config import settings
from services.support_bot_knowledge import build_voice_system_prompt

logger = logging.getLogger(__name__)

OnAudioChunk = Callable[[bytes], Awaitable[None]]
OnTranscript = Callable[[str, str], Awaitable[None]]  # role, text
OnState = Callable[[str], Awaitable[None]]  # idle | listening | thinking | speaking
OnInterrupted = Callable[[], Awaitable[None]]
OnError = Callable[[str], Awaitable[None]]

_AUDIO_QUEUE_MAX = 48
_KEEPALIVE_INTERVAL = 10          # seconds between silent-audio pings
_SILENT_FRAME = b'\x00' * 320    # 10ms of silent PCM16 @ 16kHz (160 samples × 2 bytes)


class GeminiLiveProxy:
    """Manages one Gemini Live session per WebSocket connection."""

    def __init__(self, user_role: str):
        self.user_role = user_role
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self._session = None
        self._ctx = None
        self._receive_task: Optional[asyncio.Task] = None
        self._send_worker_task: Optional[asyncio.Task] = None
        self._send_queue: asyncio.Queue[Optional[bytes]] = asyncio.Queue(maxsize=_AUDIO_QUEUE_MAX)
        self._callback_tasks: set[asyncio.Task] = set()
        self._closed = False
        self._connection_lost = False
        self._keepalive_task: Optional[asyncio.Task] = None
        self.on_audio: Optional[OnAudioChunk] = None
        self.on_transcript: Optional[OnTranscript] = None
        self.on_state: Optional[OnState] = None
        self.on_interrupted: Optional[OnInterrupted] = None
        self.on_error: Optional[OnError] = None
        self._model_responding = False

    @property
    def is_alive(self) -> bool:
        return not self._closed and self._session is not None

    def _live_config(self) -> types.LiveConnectConfig:
        return types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=types.Content(
                parts=[types.Part(text=build_voice_system_prompt(self.user_role))]
            ),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
                )
            ),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )

    async def start(self) -> None:
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY is not configured for Gemini Live")

        await self._connect_session()
        self._receive_task = asyncio.create_task(self._receive_loop())
        self._send_worker_task = asyncio.create_task(self._send_worker())
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())
        logger.info("Gemini Live session started for role=%s", self.user_role)

    async def _connect_session(self) -> None:
        self._ctx = self._client.aio.live.connect(
            model=settings.GEMINI_LIVE_MODEL,
            config=self._live_config(),
        )
        self._session = await self._ctx.__aenter__()

    def _schedule_callback(self, coro: Awaitable[None]) -> None:
        task = asyncio.create_task(coro)
        self._callback_tasks.add(task)
        task.add_done_callback(self._callback_tasks.discard)

    async def _safe_call(self, cb: Optional[Callable[..., Awaitable[None]]], *args) -> None:
        if not cb:
            return
        try:
            await cb(*args)
        except Exception:
            logger.exception("Gemini Live callback error")

    async def _receive_loop(self) -> None:
        try:
            if not self._session:
                return
            async for response in self._session.receive():
                if self._closed:
                    break
                sc = response.server_content
                if not sc:
                    continue

                if getattr(sc, "interrupted", False):
                    self._model_responding = False
                    if self.on_interrupted:
                        self._schedule_callback(self._safe_call(self.on_interrupted))
                    if self.on_state:
                        self._schedule_callback(self._safe_call(self.on_state, "listening"))

                if sc.input_transcription and sc.input_transcription.text:
                    if self.on_transcript:
                        self._schedule_callback(
                            self._safe_call(self.on_transcript, "user", sc.input_transcription.text)
                        )

                if sc.output_transcription and sc.output_transcription.text:
                    if self.on_transcript:
                        self._schedule_callback(
                            self._safe_call(self.on_transcript, "bot", sc.output_transcription.text)
                        )

                if sc.model_turn:
                    has_audio = False
                    for part in sc.model_turn.parts or []:
                        if part.inline_data and part.inline_data.data:
                            has_audio = True
                            if self.on_audio:
                                chunk = part.inline_data.data
                                self._schedule_callback(self._safe_call(self.on_audio, chunk))
                        if part.text and self.on_transcript:
                            self._schedule_callback(
                                self._safe_call(self.on_transcript, "bot", part.text)
                            )
                    if has_audio:
                        self._model_responding = True
                        if self.on_state:
                            self._schedule_callback(self._safe_call(self.on_state, "speaking"))
                    elif not self._model_responding:
                        if self.on_state:
                            self._schedule_callback(self._safe_call(self.on_state, "thinking"))

                if getattr(sc, "turn_complete", False):
                    self._model_responding = False
                    if self.on_state:
                        self._schedule_callback(self._safe_call(self.on_state, "listening"))
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            if not self._closed:
                logger.warning("Gemini Live receive ended: %s", exc)
                await self._handle_connection_lost(exc)

    async def _keepalive_loop(self) -> None:
        """Send silent audio frames periodically to prevent Gemini's
        keep-alive ping timeout (1011) when the user is not speaking."""
        try:
            while not self._closed and not self._connection_lost:
                await asyncio.sleep(_KEEPALIVE_INTERVAL)
                if self._closed or self._connection_lost or not self._session:
                    break
                # Only send keep-alive when not actively streaming user audio
                if self._send_queue.empty():
                    try:
                        await self._session.send_realtime_input(
                            audio=types.Blob(
                                data=_SILENT_FRAME,
                                mime_type="audio/pcm;rate=16000",
                            )
                        )
                    except Exception as exc:
                        if not self._closed:
                            logger.debug("Keep-alive send failed: %s", exc)
                            await self._handle_connection_lost(exc)
                        break
        except asyncio.CancelledError:
            pass

    async def _send_worker(self) -> None:
        try:
            while not self._closed:
                pcm_bytes = await self._send_queue.get()
                if pcm_bytes is None or self._closed:
                    break
                if not self._session:
                    continue
                try:
                    await self._session.send_realtime_input(
                        audio=types.Blob(data=pcm_bytes, mime_type="audio/pcm;rate=16000")
                    )
                except Exception as exc:
                    if not self._closed:
                        await self._handle_connection_lost(exc)
                    break
        except asyncio.CancelledError:
            pass

    async def _handle_connection_lost(self, exc: Exception) -> None:
        if self._closed or self._connection_lost:
            return
        self._connection_lost = True
        logger.warning("Gemini Live connection lost: %s", exc)

        # Cancel the old receive loop before reconnect
        self._session = None
        await self._disconnect_session()
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass

        # Attempt automatic reconnect (up to 2 retries)
        for attempt in range(1, 3):
            if self._closed:
                break
            logger.info("Gemini Live reconnect attempt %d/2", attempt)
            try:
                await asyncio.sleep(1.0 * attempt)
                await self._connect_session()
                self._connection_lost = False
                self._receive_task = asyncio.create_task(self._receive_loop())
                self._keepalive_task = asyncio.create_task(self._keepalive_loop())
                logger.info("Gemini Live reconnected successfully on attempt %d", attempt)
                if self.on_state:
                    await self._safe_call(self.on_state, "listening")
                return
            except Exception as retry_exc:
                logger.warning("Gemini Live reconnect attempt %d failed: %s", attempt, retry_exc)
                self._session = None
                await self._disconnect_session()

        # All retries exhausted
        if self.on_error:
            await self.on_error("Voice session disconnected. Close and reopen the assistant to try again.")

    async def _disconnect_session(self) -> None:
        if self._ctx:
            try:
                await self._ctx.__aexit__(None, None, None)
            except Exception:
                pass
            self._ctx = None

    async def send_audio_pcm16(self, pcm_bytes: bytes) -> None:
        if not self.is_alive:
            return
        try:
            self._send_queue.put_nowait(pcm_bytes)
        except asyncio.QueueFull:
            try:
                self._send_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                self._send_queue.put_nowait(pcm_bytes)
            except asyncio.QueueFull:
                pass

    async def send_text(self, text: str) -> None:
        if not self.is_alive:
            return
        try:
            await self._session.send_client_content(
                turns=[types.Content(role="user", parts=[types.Part(text=text)])],
                turn_complete=True,
            )
        except Exception as exc:
            await self._handle_connection_lost(exc)

    async def close(self) -> None:
        self._closed = True
        try:
            self._send_queue.put_nowait(None)
        except asyncio.QueueFull:
            pass

        for task in (self._send_worker_task, self._receive_task, self._keepalive_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        for task in list(self._callback_tasks):
            task.cancel()

        await self._disconnect_session()
        self._session = None
        logger.info("Gemini Live session closed")
