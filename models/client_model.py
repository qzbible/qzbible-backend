from extensions import mongo 
from bson import ObjectId
from datetime import datetime
from utils.inject_magasin_id import inject_magasin_id

class ClientModel:
     
    @staticmethod
    def get_collection():
        from extensions import mongo
        return mongo.db.clients
    
    collection = mongo.db.clients
    
    @staticmethod
    def create_client(data):
        """
        Crée un nouveau client avec les informations fournies.

        :param data: dict contenant 'nom', 'telephone', 'email', 'ville', 'quartier', 'adresse', 'password'
        :return: dict contenant le message de succès et l'ID du client créé
        """
        try:
            data = inject_magasin_id(data)
        except Exception as e:
            return {"error": str(e)}, 401

        client = {
            "nom": data["nom"],
            "created_by": data.get("created_by", None),
            "telephone": data["telephone"],
            "email": data["email"],
            "ville": data["ville"],
            "quartier": data["quartier"],
            "photo_profil": data.get("photo_profil", None),
            "magasin_id": ObjectId(data["magasin_id"]),
            "created_at": datetime.utcnow()
        }
        
        result = ClientModel.get_collection().insert_one(client)
        
        return {
            "message": "Client créé avec succès",
            "client_id": str(result.inserted_id)
        }

    @staticmethod
    def get_client_by_id(client_id):
        """
        Récupère un client par son ID.
        """
        client = ClientModel.get_collection().find_one({"_id": ObjectId(client_id)})
        if client:
            client["_id"] = str(client["_id"])
        return client

    @staticmethod
    def get_all_clients_by_magasin(magasin_id=None):
        """
        Récupère tous les clients d'un magasin donné.
        """
        if magasin_id is None:
            try:
                data = inject_magasin_id({})
                magasin_id = data["magasin_id"]
            except Exception as e:
                return {"error": str(e)}, 401

        clients = ClientModel.get_collection().find({"magasin_id": ObjectId(magasin_id)})
        return list(clients)

    @staticmethod
    def update_client(client_id, data):
        """
        Met à jour les informations d'un client existant.
        """
        update_data = {k: data[k] for k in data if k in ["nom", "telephone", "email", "ville", "quartier", "adresse"]}
        
        result = ClientModel.get_collection().update_one(
            {"_id": ObjectId(client_id)},
            {"$set": update_data}
        )
        
        return {
            "message": "Client mis à jour avec succès",
            "modified_count": result.modified_count
        }

    @staticmethod
    def delete_client(client_id):
        """
        Supprime un client par son ID.
        """
        result = ClientModel.get_collection().delete_one({"_id": ObjectId(client_id)})

        return {
            "message": "Client supprimé avec succès",
            "deleted_count": result.deleted_count
        }

    @staticmethod
    def get_all_clients(magasin_id):
        """
        Récupère tous les clients d’un magasin si précisé.
        """


        clients = ClientModel.get_collection().find({
            "magasin_id": ObjectId(magasin_id)
        })        
        return list(clients)

    @staticmethod
    def get_client_by_phone(telephone, magasin_id=None):
        """
        Récupère un client par téléphone et magasin.
        """
        query = {"telephone": telephone}
        if magasin_id is None:
            try:
                data = inject_magasin_id({})
                magasin_id = data["magasin_id"]
            except Exception:
                pass
        if magasin_id:
            query["magasin_id"] = ObjectId(magasin_id)

        return ClientModel.get_collection().find_one(query)

    @staticmethod
    def get_clients_by_ids(client_ids, magasin_id=None):
        """
        Récupère les clients dont les IDs sont dans la liste, éventuellement filtrés par magasin.
        """
        object_ids = [ObjectId(cid) for cid in client_ids]
        query = {"_id": {"$in": object_ids}}
        if magasin_id is None:
            try:
                data = inject_magasin_id({})
                magasin_id = data["magasin_id"]
            except Exception:
                magasin_id = None
        if magasin_id:
            query["magasin_id"] = ObjectId(magasin_id)

        clients = ClientModel.get_collection().find(query)
        return list(clients)
