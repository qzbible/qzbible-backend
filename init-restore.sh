#!/bin/bash
echo "Démarrage de la restauration de la base de données..."

# Attendre que MongoDB soit complètement démarré
until mongosh --eval "print(\"waited for connection\")"
do
    sleep 2
done

# Restaurer le dump
mongorestore /data/dump/

echo "Restauration terminée !"