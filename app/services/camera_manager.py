"""Hilos que procesan el video de las cámaras en el propio backend."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Any

# Si tu cámara usa OpenCV/RTSP, aquí iría cv2, etc.
# import cv2


OnIncident = Callable[[dict], "asyncio.Future[Any]"]  # callback async


@dataclass
class CameraWorker:
    """Estado de un hilo de procesamiento de cámara."""
    camera_id: str
    rtsp_url: str
    fps_target: int
    infer_every_n_frames: int
    task: asyncio.Task
    stop_event: asyncio.Event


class CameraManager:
    """
    RESPONSABILIDAD ÚNICA:
    - iniciar / parar workers de cámaras
    - mantener estado
    NO guarda en DB directamente (DIP).
    """

    def __init__(self):
        self._workers: Dict[str, CameraWorker] = {}

    def start(
        self,
        *,
        camera_id: str,
        rtsp_url: str,
        fps_target: int = 5,
        infer_every_n_frames: int = 5,
        on_incident: Optional[OnIncident] = None,
    ) -> None:
        """Arranca el hilo de una cámara si no está corriendo."""
        # ya está corriendo
        if camera_id in self._workers:
            return

        stop_event = asyncio.Event()
        task = asyncio.create_task(
            self._run_camera_loop(
                camera_id=camera_id,
                rtsp_url=rtsp_url,
                fps_target=fps_target,
                infer_every_n_frames=infer_every_n_frames,
                stop_event=stop_event,
                on_incident=on_incident,
            )
        )

        self._workers[camera_id] = CameraWorker(
            camera_id=camera_id,
            rtsp_url=rtsp_url,
            fps_target=fps_target,
            infer_every_n_frames=infer_every_n_frames,
            task=task,
            stop_event=stop_event,
        )

    def stop(self, camera_id: str) -> None:
        """Detiene el hilo de una cámara."""
        w = self._workers.get(camera_id)
        if not w:
            return
        w.stop_event.set()
        if not w.task.done():
            w.task.cancel()
        self._workers.pop(camera_id, None)

    def status(self) -> Dict[str, dict]:
        """Estado de cada hilo activo."""
        return {
            cid: {
                "running": True,
                "rtsp_url": w.rtsp_url,
                "fps_target": w.fps_target,
                "infer_every_n_frames": w.infer_every_n_frames,
            }
            for cid, w in self._workers.items()
        }

    async def _run_camera_loop(
        self,
        *,
        camera_id: str,
        rtsp_url: str,
        fps_target: int,
        infer_every_n_frames: int,
        stop_event: asyncio.Event,
        on_incident: Optional[OnIncident],
    ) -> None:
        """
        Loop de cámara (placeholder):
        - aquí iría lectura RTSP
        - cada N frames harías inferencia
        - si detectas -> on_incident(payload)
        """

        frame_count = 0
        delay = 1.0 / max(1, fps_target)

        try:
            while not stop_event.is_set():
                await asyncio.sleep(delay)
                frame_count += 1

                # Simulación: cada infer_every_n_frames genera un "incidente"
                if infer_every_n_frames > 0 and frame_count % infer_every_n_frames == 0:
                    if on_incident:
                        payload = {
                            "camera_id": camera_id,
                            "weapon_type": "knife",
                            "confidence": 0.88,
                            "evidence_url": None,
                        }
                        await on_incident(payload)

        except asyncio.CancelledError:
            # parar limpio
            return


camera_manager = CameraManager()
