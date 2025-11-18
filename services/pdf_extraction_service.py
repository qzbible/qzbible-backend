# services/pdf_extraction_service.py
import PyPDF2
import fitz  # PyMuPDF
import re
from pathlib import Path

def extract_pdf_metadata(file_path):
    """
    Extrait les métadonnées d'un fichier PDF
    """
    try:
        # Ouvrir le PDF avec PyMuPDF (plus robuste)
        doc = fitz.open(file_path)
        
        # Extraire les métadonnées de base
        metadata = doc.metadata
        total_pages = len(doc)
        
        # Extraire le titre
        title = metadata.get('title', '').strip()
        if not title:
            # Si pas de titre dans les métadonnées, utiliser le nom du fichier
            title = Path(file_path).stem.replace('_', ' ').replace('-', ' ')
            title = clean_filename_title(title)
        
        # Extraire l'auteur
        author = metadata.get('author', '').strip()
        if not author:
            # Essayer d'extraire l'auteur du contenu de la première page
            if total_pages > 0:
                first_page_text = doc[0].get_text()
                author = extract_author_from_text(first_page_text)
            if not author:
                author = 'Auteur inconnu'
        
        # Déterminer la catégorie basée sur le titre/contenu
        category = determine_category(title, metadata.get('subject', ''))
        
        # Détecter la langue (simple détection)
        language = detect_language_simple(title)
        
        # Extraire des tags potentiels
        tags = extract_tags_from_content(title, metadata.get('subject', ''))
        
        doc.close()
        
        return {
            'title': title[:200],  # Limiter à 200 caractères
            'author': author[:100],  # Limiter à 100 caractères
            'total_pages': total_pages,
            'category': category,
            'language': language,
            'tags': tags[:5]  # Maximum 5 tags
        }
        
    except Exception as e:
        # En cas d'erreur, extraire au minimum le nom du fichier
        filename = Path(file_path).stem
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
    # Supprimer les caractères indésirables
    title = re.sub(r'[_\-\.]', ' ', filename)
    # Supprimer les numéros en début/fin
    title = re.sub(r'^\d+\s*', '', title)
    title = re.sub(r'\s*\d+$', '', title)
    # Capitaliser chaque mot
    title = ' '.join(word.capitalize() for word in title.split())
    return title.strip()

def extract_author_from_text(text):
    """Extrait l'auteur potentiel du texte de la première page"""
    # Patterns communs pour trouver l'auteur
    patterns = [
        r'(?:par|by|auteur?:?)\s+([A-Z][a-z]+ [A-Z][a-z]+)',
        r'^([A-Z][a-z]+ [A-Z][a-z]+)$',  # Nom sur une ligne seule
        r'([A-Z][A-Z\s]+)',  # Nom en majuscules
    ]
    
    lines = text.split('\n')[:10]  # Analyser les 10 premières lignes
    
    for line in lines:
        line = line.strip()
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                if len(author.split()) == 2 and len(author) < 50:  # Nom raisonnable
                    return author
    
    return ''

def determine_category(title, subject):
    """Détermine la catégorie basée sur le titre et le sujet"""
    text = f"{title} {subject}".lower()
    
    # Mots-clés pour chaque catégorie
    category_keywords = {
        'theology': ['théologie', 'doctrine', 'dogmatique', 'systematic', 'theology'],
        'devotional': ['méditation', 'prière', 'devotional', 'spiritual', 'marche', 'vie chrétienne'],
        'biography': ['biographie', 'vie de', 'biography', 'témoignage'],
        'commentary': ['commentaire', 'commentary', 'explication', 'étude biblique'],
        'study': ['étude', 'formation', 'enseignement', 'study', 'cours']
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in text for keyword in keywords):
            return category
    
    return 'study'  # Par défaut

def detect_language_simple(title):
    """Détection simple de la langue basée sur des mots-clés"""
    french_words = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'à', 'pour', 'avec', 'sur', 'dans']
    english_words = ['the', 'and', 'of', 'to', 'a', 'in', 'for', 'with', 'on', 'by']
    
    title_lower = title.lower()
    
    french_count = sum(1 for word in french_words if word in title_lower)
    english_count = sum(1 for word in english_words if word in title_lower)
    
    return 'en' if english_count > french_count else 'fr'

def extract_tags_from_content(title, subject):
    """Extrait des tags potentiels du titre et sujet"""
    text = f"{title} {subject}".lower()
    
    # Tags communs dans la littérature chrétienne
    potential_tags = [
        'baptême', 'prière', 'foi', 'salut', 'grâce', 'esprit saint',
        'évangile', 'bible', 'christ', 'jésus', 'dieu', 'église',
        'nouveau converti', 'disciple', 'sanctification', 'espoir',
        'amour', 'pardon', 'rédemption', 'vie éternelle'
    ]
    
    found_tags = []
    for tag in potential_tags:
        if tag in text and len(found_tags) < 5:
            found_tags.append(tag)
    
    return found_tags