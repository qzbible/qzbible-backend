



from models.church_model import ChurchModel
from models.document_model import DocumentModel
from models.user_model import UserModel
from bson import ObjectId
from datetime import datetime, timedelta
# Services pour les documents
def create_document_service(document_data, file_info, uploaded_by):
    """Créer un nouveau document"""
    result = DocumentModel.create_document(document_data, file_info, uploaded_by)
    return result, 201

def get_documents_for_plans_service(filters=None):
    """Récupérer les documents disponibles pour les plans"""
    return DocumentModel.get_documents_for_plans(filters)

def get_document_plan_helper_service(document_id):
    """Aide à la configuration d'un plan depuis un document"""
    result = DocumentModel.get_plan_helper(document_id)
    if isinstance(result, tuple):
        return result
    return result

def update_document_structure_service(document_id, structure_data):
    """Mettre à jour la structure d'un document"""
    result, status = DocumentModel.update_structure(document_id, structure_data)
    return result, status