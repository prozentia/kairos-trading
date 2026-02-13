#!/bin/bash
# ====================================================================
# Kairos Trading - Script de deploiement production
# VPS: 158.220.103.131 | Chemin: /opt/kairos-trading
# Usage: bash scripts/deploy.sh
# ====================================================================

set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR"

echo "============================================"
echo "  Kairos Trading - Deploiement Production"
echo "============================================"
echo ""

# Verifier que le fichier .env existe
if [ ! -f .env ]; then
    echo "[ERREUR] Le fichier .env est manquant."
    echo "         Copiez .env.example en .env et remplissez les valeurs."
    echo "         cp .env.example .env"
    exit 1
fi

# 1. Pull les derniers changements
echo "[1/5] Pull des derniers changements depuis Git..."
git pull origin main

# 2. Build les images Docker
echo "[2/5] Build des images Docker..."
docker compose -f "$COMPOSE_FILE" build --no-cache

# 3. Arreter les anciens containers
echo "[3/5] Arret des containers existants..."
docker compose -f "$COMPOSE_FILE" down

# 4. Demarrer les nouveaux containers
echo "[4/5] Demarrage des containers..."
docker compose -f "$COMPOSE_FILE" up -d

# 5. Attendre que l'API soit prete puis lancer les migrations
echo "[5/5] Attente de l'API et lancement des migrations..."
echo "       Attente de la base de donnees..."
sleep 10

# Attendre que le healthcheck passe
MAX_RETRIES=30
RETRY=0
while [ $RETRY -lt $MAX_RETRIES ]; do
    if docker compose -f "$COMPOSE_FILE" exec -T api curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "       API prete."
        break
    fi
    RETRY=$((RETRY + 1))
    echo "       Attente... ($RETRY/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY -eq $MAX_RETRIES ]; then
    echo "[ERREUR] L'API n'a pas repondu au healthcheck dans le delai imparti."
    echo "         Verification des logs..."
    docker compose -f "$COMPOSE_FILE" logs --tail=20 api
    exit 1
fi

# Lancer les migrations Alembic
echo "       Lancement des migrations Alembic..."
docker compose -f "$COMPOSE_FILE" exec -T api alembic upgrade head || {
    echo "[ERREUR] Les migrations Alembic ont echoue."
    docker compose -f "$COMPOSE_FILE" logs --tail=20 api
    exit 1
}

# Seed des strategies par defaut
echo "       Seed des strategies par defaut..."
docker compose -f "$COMPOSE_FILE" exec -T api python -m scripts.seed_strategies || {
    echo "[WARN] Le seed des strategies a echoue (non-bloquant)."
}

echo ""
echo "============================================"
echo "  Deploiement termine avec succes !"
echo "============================================"
echo ""
echo "  URL: https://kairos.prozentia.com"
echo "  API: https://kairos.prozentia.com/api/docs"
echo ""
echo "  Commandes utiles:"
echo "    docker compose -f $COMPOSE_FILE logs -f"
echo "    docker compose -f $COMPOSE_FILE ps"
echo "    docker compose -f $COMPOSE_FILE exec api alembic upgrade head"
echo ""
