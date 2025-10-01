from extensions import mongo
from bson import ObjectId
from datetime import datetime



class ImageStaffModel:
    collection = mongo.db.images_staff  # Collection MongoDB pour les images de staff
    
    @staticmethod
    def ajouter_image(data):
        data["created_at"] = datetime.utcnow()
        data["updated_at"] = datetime.utcnow()
        result = ImageStaffModel.collection.insert_one(data)
        return str(result.inserted_id)
    
    
    @staticmethod
    def get_all_images():
        """
        Récupère toutes les images de staff.
        """
        return list(ImageStaffModel.collection.find())  
    
    @staticmethod
    def get_image_by_critere(nom=None, categorie=None, description=None, tag=None):
        filtre = {}
        
        if nom:
            filtre["nom"] = {"$regex": nom, "$options": "i"}  # Recherche insensible à la casse
        
        if categorie:
            filtre["categorie"] = {"$regex": categorie, "$options": "i"}
        if description:
            filtre["description"] = {"$regex": description, "$options": "i"}
            
        if tag:
            filtre["tags"] = {"$in": [tag]}
            
        return list(ImageStaffModel.collection.find(filtre))
    
    
    @staticmethod
    def supprimer_image(image_id):
        """
        Supprime une image de staff par son ID.
        """
        if not ObjectId.is_valid(image_id):
            return {"error": "ID non valide."}, 400
        
        result = ImageStaffModel.collection.delete_one({"_id": ObjectId(image_id)})
        
        if result.deleted_count == 0:
            return {"error": "Image non trouvée."}, 404
        
        return {"message": "Image supprimée avec succès."}, 200