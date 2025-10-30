# services/catalog_service.py

from bson import ObjectId
from models.catalog_model import CatalogModel, CatalogRatingModel, CatalogDownloadModel
from models.section_model import SectionModel
from models.chapter_model import ChapterModel
from models.quiz_model import QuizModel
from models.church_model import ChurchModel

def publish_to_catalog_service(content_type, content_id, church_id, tags=None):
    """
    Publie du contenu au catalogue public.
    """
    # Vérifier si déjà publié
    if CatalogModel.check_if_published(content_type, content_id):
        return {"message": "Ce contenu est déjà publié au catalogue"}, 400
    
    # Récupérer le contenu selon le type
    content = None
    preview = {}
    
    if content_type == "section":
        content = SectionModel.get_section_by_id(content_id)
        if content:
            # Calculer les stats de la section
            chapters_count = ChapterModel.count_by_section(content_id)
            quiz_count = 0
            # TODO: Calculer le nombre total de quiz dans la section
            
            preview = {
                "chapters_count": chapters_count,
                "quiz_count": quiz_count,
                "avg_rating": 0
            }
    
    elif content_type == "chapter":
        content = ChapterModel.get_chapter_by_id(content_id)
        if content:
            quiz_count = QuizModel.count_by_chapter(content_id)
            preview = {
                "chapters_count": 1,
                "quiz_count": quiz_count,
                "avg_rating": 0
            }
    
    elif content_type == "quiz":
        content = QuizModel.get_quiz_by_id(content_id)
        if content:
            preview = {
                "chapters_count": 0,
                "quiz_count": 1,
                "avg_rating": 0
            }
    
    if not content:
        return {"message": "Contenu non trouvé"}, 404
    
    # Récupérer le nom de l'église
    church = ChurchModel.get_church_by_id(church_id)
    church_name = church.get("name", "") if church else ""
    
    # Publier
    data = {
        "content_type": content_type,
        "content_id": content_id,
        "church_id": church_id,
        "church_name": church_name,
        "title": content.get("title", ""),
        "description": content.get("description", ""),
        "preview": preview,
        "tags": tags or []
    }
    
    result = CatalogModel.publish_to_catalog(data)
    return result, 201


def get_catalog_items_service(filters=None, page=1, per_page=20):
    """
    Récupère les éléments du catalogue avec pagination.
    """
    skip = (page - 1) * per_page
    sort_by = filters.get("sort_by", "downloads") if filters else "downloads"
    
    items = CatalogModel.get_all_catalog_items(filters, sort_by, skip, per_page)
    total = CatalogModel.count_catalog_items(filters)
    
    # Convertir les ObjectId
    for item in items:
        item["_id"] = str(item["_id"])
        item["content_id"] = str(item["content_id"])
        item["church_id"] = str(item["church_id"])
    
    return {
        "data": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }


def get_catalog_item_detail_service(catalog_item_id, user_id=None):
    """
    Récupère les détails d'un élément du catalogue.
    """
    item = CatalogModel.get_catalog_item_by_id(catalog_item_id)
    
    if not item:
        return {"message": "Élément non trouvé"}, 404
    
    # Ajouter les avis récents
    ratings = CatalogRatingModel.get_ratings_by_catalog_item(catalog_item_id, 0, 5)
    for rating in ratings:
        rating["_id"] = str(rating["_id"])
        rating["catalog_item_id"] = str(rating["catalog_item_id"])
        rating["user_id"] = str(rating["user_id"])
        rating["church_id"] = str(rating["church_id"])
    
    item["recent_ratings"] = ratings
    
    # Si un utilisateur est connecté, récupérer sa note
    if user_id:
        user_rating = CatalogRatingModel.get_user_rating(catalog_item_id, user_id)
        if user_rating:
            user_rating["_id"] = str(user_rating["_id"])
            user_rating["catalog_item_id"] = str(user_rating["catalog_item_id"])
            user_rating["user_id"] = str(user_rating["user_id"])
            user_rating["church_id"] = str(user_rating["church_id"])
        item["user_rating"] = user_rating
    
    return item


def import_from_catalog_service(catalog_item_id, church_id, user_id, target_section_id=None):
    """
    Importe du contenu depuis le catalogue.
    """
    # Récupérer l'élément du catalogue
    catalog_item = CatalogModel.get_catalog_item_by_id(catalog_item_id)
    
    if not catalog_item:
        return {"message": "Élément du catalogue non trouvé"}, 404
    
    content_type = catalog_item["content_type"]
    source_content_id = catalog_item["content_id"]
    
    # Vérifier si déjà téléchargé
    already_downloaded = CatalogDownloadModel.check_if_downloaded(catalog_item_id, church_id)
    
    # Importer selon le type
    new_content_id = None
    
    if content_type == "section":
        # Cloner la section complète
        from services.section_service import clone_section_service
        result, status = clone_section_service(source_content_id, church_id, user_id)
        if status == 201:
            new_content_id = result["section_id"]
    
    elif content_type == "chapter":
        # Cloner le chapitre
        if not target_section_id:
            return {"message": "target_section_id est requis pour importer un chapitre"}, 400
        
        from services.chapter_service import clone_chapter_service
        result, status = clone_chapter_service(source_content_id, target_section_id, church_id, user_id)
        if status == 201:
            new_content_id = result["chapter_id"]
    
    elif content_type == "quiz":
        # Cloner le quiz
        if not target_section_id:
            return {"message": "target_section_id est requis pour importer un quiz"}, 400
        
        # TODO: Implémenter le clonage de quiz vers un chapitre spécifique
        pass
    
    if not new_content_id:
        return {"message": "Erreur lors de l'importation"}, 500
    
    # Incrémenter le compteur de téléchargements
    CatalogModel.increment_downloads(catalog_item_id)
    
    # Enregistrer le téléchargement
    if not already_downloaded:
        CatalogDownloadModel.record_download({
            "catalog_item_id": catalog_item_id,
            "church_id": church_id,
            "downloaded_by": user_id,
            "content_type": content_type,
            "content_id": new_content_id
        })
    
    return {
        "message": "Contenu importé avec succès",
        "content_type": content_type,
        "new_content_id": new_content_id,
        "already_downloaded": already_downloaded
    }, 201


def rate_catalog_item_service(catalog_item_id, user_id, church_id, rating, comment=None):
    """
    Note un élément du catalogue.
    """
    # Vérifier que l'élément existe
    catalog_item = CatalogModel.get_catalog_item_by_id(catalog_item_id)
    if not catalog_item:
        return {"message": "Élément du catalogue non trouvé"}, 404
    
    # Ajouter/mettre à jour la note
    result = CatalogRatingModel.add_rating({
        "catalog_item_id": catalog_item_id,
        "user_id": user_id,
        "church_id": church_id,
        "rating": rating,
        "comment": comment
    })
    
    # Mettre à jour la note moyenne
    CatalogModel.update_rating(catalog_item_id, rating)
    
    return result, 200


def unpublish_from_catalog_service(catalog_item_id, church_id):
    """
    Retire un contenu du catalogue.
    """
    catalog_item = CatalogModel.get_catalog_item_by_id(catalog_item_id)
    
    if not catalog_item:
        return {"message": "Élément non trouvé"}, 404
    
    if catalog_item["church_id"] != str(church_id):
        return {"message": "Accès non autorisé"}, 403
    
    result = CatalogModel.unpublish_from_catalog(catalog_item_id)
    return result, 200


def get_my_published_content_service(church_id):
    """
    Récupère tout le contenu publié par mon église.
    """
    items = CatalogModel.get_catalog_items_by_church(church_id)
    
    for item in items:
        item["_id"] = str(item["_id"])
        item["content_id"] = str(item["content_id"])
        item["church_id"] = str(item["church_id"])
    
    return items


def get_catalog_stats_service():
    """
    Récupère les statistiques du catalogue.
    """
    return CatalogModel.get_catalog_stats()


def get_popular_tags_service(limit=20):
    """
    Récupère les tags les plus populaires.
    """
    return CatalogModel.get_popular_tags(limit)


def search_catalog_service(search_term):
    """
    Recherche dans le catalogue.
    """
    items = CatalogModel.search_catalog(search_term, 20)
    
    for item in items:
        item["_id"] = str(item["_id"])
        item["content_id"] = str(item["content_id"])
        item["church_id"] = str(item["church_id"])
    
    return items