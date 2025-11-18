# services/pdf_extraction_service.py (version simplifiée)
import os
from pathlib import Path
import re

def extract_pdf_metadata(file_path):
    """
    Extrait les métadonnées basiques d'un fichier PDF sans librairies externes
    """
    try:
        # Extraire les informations basées sur le nom de fichier
        filename = Path(file_path).stem
        file_size = os.path.getsize(file_path)
        
        # Nettoyer le titre du nom de fichier
        title = clean_filename_title(filename)
        
        # Essayer de détecter l'auteur dans le nom de fichier
        author = extract_author_from_filename(filename)
        
        # Déterminer la catégorie basée sur le titre
        category = determine_category_simple(title)
        
        # Détecter la langue
        language = detect_language_simple(title)
        
        return {
            'title': title[:200],
            'author': author[:100] if author else 'Auteur inconnu',
            'total_pages': 0,  # Ne peut pas être déterminé sans librairie PDF
            'category': category,
            'language': language,
            'tags': []
        }
        
    except Exception as e:
        # Fallback complet
        filename = Path(file_path).stem if file_path else "Document"
        return {
            'title': clean_filename_title(filename),
            'author': 'Auteur inconnu',
            'total_pages': 0,
            'category': 'study',
            'language': 'fr',
            'tags': []
        }

def clean_filename_title(filename):
    """Nettoie le nom de fichier pour en faire un titre lisible"""
    # Remplacer les caractères de séparation par des espaces
    title = re.sub(r'[_\-\.]', ' ', filename)
    # Supprimer les numéros/dates en début
    title = re.sub(r'^\d{8}_\d{6}_', '', title)  # Timestamp format
    title = re.sub(r'^\d+\s*', '', title)
    # Supprimer les extensions restantes
    title = re.sub(r'\.(pdf|doc|docx)$', '', title, re.IGNORECASE)
    # Capitaliser chaque mot
    words = title.split()
    title = ' '.join(word.capitalize() for word in words if len(word) > 1)
    return title.strip() or "Document"

def extract_author_from_filename(filename):
    """Essaie d'extraire un auteur du nom de fichier"""
    # Patterns pour détecter un auteur dans le nom de fichier
    patterns = [
        r'(?:par|by)[\s_\-]+([A-Za-z]+[\s_\-]+[A-Za-z]+)',
        r'^([A-Z][a-z]+[\s_\-]+[A-Z][a-z]+)',  # Nom au début
        r'([A-Z][a-z]+[\s_\-]+[A-Z][a-z]+)[\s_\-]',  # Nom suivi d'espace
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename.replace('_', ' ').replace('-', ' '))
        if match:
            author = match.group(1).replace('_', ' ').replace('-', ' ')
            return ' '.join(word.capitalize() for word in author.split())
    
    return None

def determine_category_simple(title):
    """Détermine la catégorie basée sur le titre"""
    title_lower = title.lower()
    
    if any(word in title_lower for word in ['théologie', 'doctrine', 'theology']):
        return 'theology'
    elif any(word in title_lower for word in ['méditation', 'prière', 'marche', 'vie']):
        return 'devotional'
    elif any(word in title_lower for word in ['biographie', 'vie de', 'biography']):
        return 'biography'
    elif any(word in title_lower for word in ['commentaire', 'commentary', 'explication']):
        return 'commentary'
    else:
        return 'study'

def detect_language_simple(title):
    """Détection simple de la langue"""
    french_indicators = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'à', 'pour', 'avec', 'sur', 'dans', 'une', 'un']
    english_indicators = ['the', 'and', 'of', 'to', 'a', 'in', 'for', 'with', 'on', 'by']
    
    title_lower = title.lower()
    
    french_score = sum(1 for word in french_indicators if word in title_lower)
    english_score = sum(1 for word in english_indicators if word in title_lower)
    
    return 'en' if english_score > french_score else 'fr'

def add_document_urls(doc, request_host=None):
    """Ajouter les URLs de visualisation et téléchargement"""
    doc_id = str(doc["_id"])
    
    # Utiliser l'host de la requête ou un host par défaut
    if request_host:
        base_url = f"https://{request_host}"
    else:
        base_url = "https://dev-backend.qzbible.com"
    
    doc["view_url"] = f"{base_url}/api/documents/view/{doc_id}"
    doc["download_url"] = f"{base_url}/api/documents/download/{doc_id}"
    return doc