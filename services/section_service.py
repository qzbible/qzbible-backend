# services/section_service.py

from werkzeug.utils import secure_filename
from flask import current_app
import os
from bson import ObjectId
from models.section_model import SectionModel
from models.user_model import UserModel

def create_section_service(data, icon_file=None):
    """
    Crée une nouvelle section avec gestion de l'icône.
    """
    icon_filename = None
    if icon_file:
        filename = secure_filename(icon_file.filename)
        icon_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        icon_file.save(icon_path)
        icon_filename = filename
    
    data["icon"] = icon_filename
    
    # Calculer l'ordre automatiquement si non fourni
    if not data.get("order"):
        data["order"] = SectionModel.get_next_order(data["church_id"])
    
    result = SectionModel.create_section(data)
    return result, 201


def get_all_sections_service(church_id, is_sequential=None):
    """
    Récupère toutes les sections d'une église.
    """
    if isinstance(church_id, dict) and "$oid" in church_id:
        church_id = church_id["$oid"]
    
    sections = SectionModel.get_all_sections_by_church(church_id, is_sequential)
    
    for section in sections:
        section["_id"] = str(section["_id"])
        section["church_id"] = str(section["church_id"])
        if section.get("created_by"):
            section["created_by"] = str(section["created_by"])
        if section.get("source_section_id"):
            section["source_section_id"] = str(section["source_section_id"])
    
    return sections


def get_section_by_id_service(section_id):
    """
    Récupère une section par son ID.
    """
    section = SectionModel.get_section_by_id(section_id)
    return section


def update_section_service(section_id, data, icon_file=None):
    """
    Met à jour une section.
    """
    if icon_file:
        filename = secure_filename(icon_file.filename)
        icon_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        icon_file.save(icon_path)
        data["icon"] = filename
    
    return SectionModel.update_section(section_id, data)


def delete_section_service(section_id):
    """
    Supprime une section.
    """
    # Vérifier s'il y a des chapitres associés
    chapters_count = SectionModel.count_chapters_by_section(section_id)
    if chapters_count > 0:
        return {
            "message": f"Impossible de supprimer cette section. Elle contient {chapters_count} chapitre(s).",
            "chapters_count": chapters_count
        }, 400
    
    return SectionModel.delete_section(section_id), 200


def get_catalog_service(page=1, per_page=20):
    """
    Récupère le catalogue des sections publiques.
    """
    skip = (page - 1) * per_page
    sections = SectionModel.get_public_sections(skip=skip, limit=per_page)
    total = SectionModel.count_public_sections()
    
    for section in sections:
        section["_id"] = str(section["_id"])
        section["church_id"] = str(section["church_id"])
        if section.get("created_by"):
            section["created_by"] = str(section["created_by"])
        if section.get("source_section_id"):
            section["source_section_id"] = str(section["source_section_id"])
    
    return {
        "sections": sections,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    }


def publish_section_service(section_id):
    """
    Publie une section dans le catalogue.
    """
    success = SectionModel.publish_section(section_id)
    if success:
        return {"message": "Section publiée dans le catalogue avec succès"}, 200
    return {"message": "Erreur lors de la publication"}, 500


def unpublish_section_service(section_id):
    """
    Retire une section du catalogue.
    """
    success = SectionModel.unpublish_section(section_id)
    if success:
        return {"message": "Section retirée du catalogue avec succès"}, 200
    return {"message": "Erreur lors du retrait"}, 500


def clone_section_service(section_id, new_church_id, cloned_by):
    """
    Clone une section publique vers une nouvelle église.
    """
    original_section = SectionModel.get_section_by_id(section_id)
    
    if not original_section:
        return {"message": "Section non trouvée"}, 404
    
    if not original_section.get("is_public") and not original_section.get("is_template"):
        return {"message": "Cette section n'est pas disponible dans le catalogue"}, 403
    
    # Créer la nouvelle section
    cloned_data = {
        "church_id": new_church_id,
        "title": original_section["title"],
        "description": original_section.get("description", ""),
        "order": SectionModel.get_next_order(new_church_id),
        "is_sequential": original_section.get("is_sequential", True),
        "icon": original_section.get("icon"),
        "is_public": False,
        "is_template": False,
        "source_section_id": section_id,
        "created_by": cloned_by
    }
    
    result = SectionModel.create_section(cloned_data)
    
    # TODO: Cloner aussi les chapitres et quiz associés
    
    return {
        "message": "Section clonée avec succès dans votre église",
        "section_id": result["section_id"]
    }, 201


def get_sections_with_creator_info(church_id):
    """
    Récupère les sections avec les infos des créateurs.
    """
    sections = SectionModel.get_all_sections_by_church(church_id)
    
    # Récupérer les IDs des créateurs
    creator_ids = list({
        str(section.get("created_by"))
        for section in sections
        if section.get("created_by") is not None
    })
    
    # Récupérer les infos des utilisateurs
    users = UserModel.collection.find(
        {"_id": {"$in": [ObjectId(uid) for uid in creator_ids]}}
    )
    user_map = {str(user["_id"]): user for user in users}
    
    # Enrichir les sections
    result = []
    for section in sections:
        section["_id"] = str(section["_id"])
        section["church_id"] = str(section["church_id"])
        
        creator_id = str(section.get("created_by", ""))
        if creator_id and creator_id in user_map:
            section["created_by_name"] = user_map[creator_id].get("name", "")
            section["created_by_first_name"] = user_map[creator_id].get("first_name", "")
        else:
            section["created_by_name"] = ""
            section["created_by_first_name"] = ""
        
        if section.get("source_section_id"):
            section["source_section_id"] = str(section["source_section_id"])
        
        result.append(section)
    
    return result