from prometheus_client import start_http_server, Gauge
import os
import subprocess
import json
import logging

igpu_engines_blitter_0_busy = Gauge(
    "igpu_engines_blitter_0_busy", "Blitter 0 busy utilisation %"
)
igpu_engines_blitter_0_sema = Gauge(
    "igpu_engines_blitter_0_sema", "Blitter 0 sema utilisation %"
)
igpu_engines_blitter_0_wait = Gauge(
    "igpu_engines_blitter_0_wait", "Blitter 0 wait utilisation %"
)

igpu_engines_render_3d_0_busy = Gauge(
    "igpu_engines_render_3d_0_busy", "Render 3D 0 busy utilisation %"
)
igpu_engines_render_3d_0_sema = Gauge(
    "igpu_engines_render_3d_0_sema", "Render 3D 0 sema utilisation %"
)
igpu_engines_render_3d_0_wait = Gauge(
    "igpu_engines_render_3d_0_wait", "Render 3D 0 wait utilisation %"
)

igpu_engines_video_0_busy = Gauge(
    "igpu_engines_video_0_busy", "Video 0 busy utilisation %"
)
igpu_engines_video_0_sema = Gauge(
    "igpu_engines_video_0_sema", "Video 0 sema utilisation %"
)
igpu_engines_video_0_wait = Gauge(
    "igpu_engines_video_0_wait", "Video 0 wait utilisation %"
)

igpu_engines_video_enhance_0_busy = Gauge(
    "igpu_engines_video_enhance_0_busy", "Video Enhance 0 busy utilisation %"
)
igpu_engines_video_enhance_0_sema = Gauge(
    "igpu_engines_video_enhance_0_sema", "Video Enhance 0 sema utilisation %"
)
igpu_engines_video_enhance_0_wait = Gauge(
    "igpu_engines_video_enhance_0_wait", "Video Enhance 0 wait utilisation %"
)

igpu_frequency_actual = Gauge("igpu_frequency_actual", "Frequency actual MHz")
igpu_frequency_requested = Gauge("igpu_frequency_requested", "Frequency requested MHz")

igpu_imc_bandwidth_reads = Gauge("igpu_imc_bandwidth_reads", "IMC reads MiB/s")
igpu_imc_bandwidth_writes = Gauge("igpu_imc_bandwidth_writes", "IMC writes MiB/s")

igpu_interrupts = Gauge("igpu_interrupts", "Interrupts/s")

igpu_period = Gauge("igpu_period", "Period ms")

igpu_power_gpu = Gauge("igpu_power_gpu", "GPU power W")
igpu_power_package = Gauge("igpu_power_package", "Package power W")

igpu_rc6 = Gauge("igpu_rc6", "RC6 %")

MAX_BUFFER_SIZE = 1_048_576  # 1 MiB


def _engine(data, name):
    engines = data.get("engines", {})
    return engines.get(name + "/0") or engines.get(name) or {}


def update(data):
    blitter = _engine(data, "Blitter")
    igpu_engines_blitter_0_busy.set(blitter.get("busy", 0.0))
    igpu_engines_blitter_0_sema.set(blitter.get("sema", 0.0))
    igpu_engines_blitter_0_wait.set(blitter.get("wait", 0.0))

    render = _engine(data, "Render/3D")
    igpu_engines_render_3d_0_busy.set(render.get("busy", 0.0))
    igpu_engines_render_3d_0_sema.set(render.get("sema", 0.0))
    igpu_engines_render_3d_0_wait.set(render.get("wait", 0.0))

    video = _engine(data, "Video")
    igpu_engines_video_0_busy.set(video.get("busy", 0.0))
    igpu_engines_video_0_sema.set(video.get("sema", 0.0))
    igpu_engines_video_0_wait.set(video.get("wait", 0.0))

    venh = _engine(data, "VideoEnhance")
    igpu_engines_video_enhance_0_busy.set(venh.get("busy", 0.0))
    igpu_engines_video_enhance_0_sema.set(venh.get("sema", 0.0))
    igpu_engines_video_enhance_0_wait.set(venh.get("wait", 0.0))

    igpu_frequency_actual.set(data.get("frequency", {}).get("actual", 0))
    igpu_frequency_requested.set(data.get("frequency", {}).get("requested", 0))

    igpu_imc_bandwidth_reads.set(data.get("imc-bandwidth", {}).get("reads", 0))
    igpu_imc_bandwidth_writes.set(data.get("imc-bandwidth", {}).get("writes", 0))

    igpu_interrupts.set(data.get("interrupts", {}).get("count", 0))

    igpu_period.set(data.get("period", {}).get("duration", 0))

    igpu_power_gpu.set(data.get("power", {}).get("GPU", 0))
    igpu_power_package.set(data.get("power", {}).get("Package", 0))

    igpu_rc6.set(data.get("rc6", {}).get("value", 0))


if __name__ == "__main__":
    debug = logging.DEBUG if os.getenv("DEBUG", "") in ("true", "1", "yes") else logging.INFO
    logging.basicConfig(format="%(asctime)s - %(message)s", level=debug)

    start_http_server(9922)

    try:
        period = int(os.getenv("REFRESH_PERIOD_MS", "10000"))
    except (ValueError, TypeError):
        period = 10000

    if period <= 0:
        period = 10000

    device = os.getenv("DEVICE")

    cmd = ["intel_gpu_top", "-J", "-s", str(period)]
    if device is not None:
        cmd += ["-d", device]

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    logging.info("Started intel_gpu_top with period=%s", period)
    output = ""
    depth = 0

    try:
        for line in process.stdout:
            line = line.decode("utf-8").strip()

            if not line or line in ("[", "]", ","):
                continue

            output += line
            depth += line.count("{") - line.count("}")

            if len(output) > MAX_BUFFER_SIZE:
                logging.warning("Output buffer exceeded max size, resetting")
                output = ""
                depth = 0

            if depth == 0 and output:
                try:
                    data = json.loads(output.strip(","))
                    logging.debug(data)
                    update(data)
                    output = ""
                except json.JSONDecodeError:
                    continue

        process.kill()
        process.wait()

        stderr_output = process.stderr.read().decode("utf-8", errors="replace").strip()
        if process.returncode != 0:
            logging.error("intel_gpu_top exited with code %s: %s", process.returncode, stderr_output or "(no stderr)")
        elif stderr_output:
            logging.warning("intel_gpu_top stderr: %s", stderr_output)

    finally:
        if process.poll() is None:
            process.kill()
            process.wait()

    logging.info("Finished")
