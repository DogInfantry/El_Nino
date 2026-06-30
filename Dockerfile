# ENSO Macro Risk Desk — Hugging Face Space (Docker SDK).
#
# Panel/Bokeh is a long-running WebSocket server, so it can't run as a Gradio
# or static Space — it needs a real container. HF serves the container at the
# Space subdomain root on port 7860.
#
# Build is wheels-only (pandas/numpy/scipy/statsmodels all ship manylinux
# wheels for 3.12) so there's no compile step — a couple of minutes on free
# CPU Basic. The app only reads the parquet caches baked into the image.

FROM python:3.12-slim

# HF best practice: run as a non-root user with a writable HOME.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

WORKDIR /home/user/app

COPY --chown=user requirements-space.txt .
RUN pip install --no-cache-dir --user -r requirements-space.txt

# Bring in the dashboard, the imported data modules, and the parquet caches.
COPY --chown=user . .

EXPOSE 7860

# app.py serves the landing at "/" and the other 8 pages at their route slugs
# (the exact names the landing's nav bar + leaderboard link to). PORT and the
# allowed websocket origin (the Space's public host) come from the environment.
ENV PORT=7860 \
    WS_ORIGIN=doginfantry-enso-macro-risk-desk.hf.space
CMD ["python", "app.py"]
