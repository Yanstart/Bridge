# =====================================================================
# Bridge Core - image Python minimale
# Build : docker build -t iot-bridge:dev .
# Run   : compose up bridge
# =====================================================================
FROM python:3.12-slim

# Variables d'environnement par defaut
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    BRIDGE_PORT=8080

# Repertoire de travail
WORKDIR /app

# Dependances systeme (socat eventuel pour pseudo-tty, curl pour healthcheck)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Installation des dependances Python
# (build context = ./bridge ; copie pyproject + src puis pip install)
COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --upgrade pip \
    && pip install .

# Utilisateur non-root pour la securite
RUN useradd --create-home --uid 10001 bridge \
    && chown -R bridge:bridge /app
USER bridge

# Exposition
EXPOSE 8080

# Healthcheck simple : /health renvoie 200
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://localhost:8080/health || exit 1

# Lancement
CMD ["bridge-server"]
