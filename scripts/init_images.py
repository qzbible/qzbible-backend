# scripts/init_images.py
import os
import shutil
from datetime import datetime
from werkzeug.utils import secure_filename
from models.image_staff_model import ImageStaffModel


def init_images_from_local(source_folder, categorie_default="general", app_config=None):
    """
    Initialise les images depuis un dossier local vers le serveur
    
    :param source_folder: Chemin du dossier contenant les images à importer
    :param categorie_default: Catégorie par défaut pour les images
    :param app_config: Configuration Flask (pour obtenir STAFF_IMAGE_FOLDER)
    :return: Dictionnaire avec le résultat de l'opération
    """
    print("\n" + "="*60)
    print("🚀 INITIALISATION DES IMAGES DEPUIS DOSSIER LOCAL")
    print("="*60 + "\n")
    
    # Vérifier que le dossier source existe
    if not os.path.exists(source_folder):
        print(f"❌ Erreur : Le dossier '{source_folder}' n'existe pas!")
        return {"success": False, "message": f"Dossier '{source_folder}' introuvable"}
    
    # Obtenir le dossier de destination
    if app_config:
        destination_folder = app_config.get("STAFF_IMAGE_FOLDER")
    else:
        from config import Config
        destination_folder = Config.STAFF_IMAGE_FOLDER
    
    # Créer le dossier de destination s'il n'existe pas
    os.makedirs(destination_folder, exist_ok=True)
    print(f"📁 Dossier source      : {source_folder}")
    print(f"📁 Dossier destination : {destination_folder}\n")
    
    # Extensions d'images acceptées
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp'}
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    imported_images = []
    errors_list = []
    
    # Parcourir tous les fichiers du dossier source
    try:
        files = os.listdir(source_folder)
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du dossier : {str(e)}")
        return {"success": False, "message": str(e)}
    
    total_files = len(files)
    
    print(f"📊 {total_files} fichier(s) trouvé(s) dans le dossier\n")
    
    if total_files == 0:
        print("⚠️  Le dossier est vide!")
        return {
            "success": True,
            "imported": 0,
            "errors": 0,
            "skipped": 0,
            "total": 0,
            "images": []
        }
    
    for index, filename in enumerate(files, 1):
        source_path = os.path.join(source_folder, filename)
        
        # Ignorer les dossiers
        if os.path.isdir(source_path):
            print(f"[{index}/{total_files}] ⏭️  Ignoré (dossier) : {filename}")
            skipped_count += 1
            continue
        
        # Ignorer les fichiers cachés
        if filename.startswith('.'):
            print(f"[{index}/{total_files}] ⏭️  Ignoré (fichier caché) : {filename}")
            skipped_count += 1
            continue
        
        # Vérifier l'extension du fichier
        _, ext = os.path.splitext(filename)
        if ext.lower() not in valid_extensions:
            print(f"[{index}/{total_files}] ⏭️  Ignoré (extension invalide) : {filename}")
            skipped_count += 1
            continue
        
        # Sécuriser le nom du fichier
        secure_name = secure_filename(filename)
        
        # Vérifier si le fichier existe déjà
        destination_path = os.path.join(destination_folder, secure_name)
        if os.path.exists(destination_path):
            print(f"[{index}/{total_files}] ⏭️  Ignoré (fichier existe déjà) : {filename}")
            skipped_count += 1
            continue
        
        print(f"[{index}/{total_files}] 📷 Traitement : {filename}")
        
        try:
            # Copier le fichier
            shutil.copy2(source_path, destination_path)
            print(f"           ✓ Fichier copié : {secure_name}")
            
            # Préparer les données pour la base de données
            # Nettoyer le nom : retirer l'extension et formater
            nom_image = os.path.splitext(filename)[0]
            nom_image = nom_image.replace('_', ' ').replace('-', ' ').strip()
            nom_image = ' '.join(word.capitalize() for word in nom_image.split())
            
            image_data = {
                "nom": nom_image,
                "description": f"Image importée depuis {os.path.basename(source_folder)}",
                "categorie": categorie_default,
                "filename": secure_name,
                "tags": ["import", "local", categorie_default],
            }
            
            # Enregistrer en base de données
            image_id = ImageStaffModel.ajouter_image(image_data)
            print(f"           ✓ Enregistré en DB (ID: {image_id})")
            
            imported_images.append({
                "filename": secure_name,
                "id": image_id,
                "nom": nom_image,
                "categorie": categorie_default
            })
            
            success_count += 1
            
        except Exception as e:
            error_msg = f"Erreur avec {filename}: {str(e)}"
            print(f"           ✗ {error_msg}")
            errors_list.append(error_msg)
            error_count += 1
            
            # Si le fichier a été copié mais pas enregistré en DB, le supprimer
            if os.path.exists(destination_path):
                try:
                    os.remove(destination_path)
                    print(f"           ↺ Fichier supprimé suite à l'erreur")
                except:
                    pass
        
        print()  # Ligne vide pour la lisibilité
    
    # Résumé final
    print("="*60)
    print("📊 RÉSUMÉ DE L'INITIALISATION")
    print("="*60)
    print(f"✅ Images importées avec succès : {success_count}")
    print(f"❌ Erreurs rencontrées         : {error_count}")
    print(f"⏭️  Fichiers ignorés            : {skipped_count}")
    print(f"📁 Total de fichiers traités   : {total_files}")
    
    if success_count > 0:
        print(f"\n🎉 Images disponibles à l'URL : /uploads/staff_images/<filename>")
    
    if errors_list:
        print(f"\n⚠️  Détails des erreurs :")
        for error in errors_list:
            print(f"   - {error}")
    
    print("="*60 + "\n")
    
    return {
        "success": True,
        "imported": success_count,
        "errors": error_count,
        "skipped": skipped_count,
        "total": total_files,
        "images": imported_images,
        "errors_details": errors_list
    }


def get_images_stats(app_config=None):
    """
    Récupère les statistiques sur les images
    
    :param app_config: Configuration Flask
    :return: Dictionnaire avec les statistiques
    """
    from models.image_staff_model import ImageStaffModel
    
    # Obtenir le dossier de destination
    if app_config:
        destination_folder = app_config.get("STAFF_IMAGE_FOLDER")
    else:
        from config import Config
        destination_folder = Config.STAFF_IMAGE_FOLDER
    
    # Compter les images en DB
    images_db = ImageStaffModel.get_all_images()
    count_db = len(images_db)
    
    # Compter les fichiers physiques
    count_files = 0
    if os.path.exists(destination_folder):
        files = [f for f in os.listdir(destination_folder) 
                if os.path.isfile(os.path.join(destination_folder, f)) 
                and not f.startswith('.')]
        count_files = len(files)
    
    # Compter par catégorie
    categories = {}
    for img in images_db:
        cat = img.get('categorie', 'sans_categorie')
        categories[cat] = categories.get(cat, 0) + 1
    
    return {
        "total_db": count_db,
        "total_files": count_files,
        "categories": categories,
        "folder": destination_folder
    }


def verify_images_integrity(app_config=None):
    """
    Vérifie l'intégrité entre la base de données et les fichiers physiques
    
    :param app_config: Configuration Flask
    :return: Dictionnaire avec le résultat de la vérification
    """
    from models.image_staff_model import ImageStaffModel
    
    print("\n" + "="*60)
    print("🔍 VÉRIFICATION DE L'INTÉGRITÉ DES IMAGES")
    print("="*60 + "\n")
    
    # Obtenir le dossier de destination
    if app_config:
        destination_folder = app_config.get("STAFF_IMAGE_FOLDER")
    else:
        from config import Config
        destination_folder = Config.STAFF_IMAGE_FOLDER
    
    # Images en DB
    images_db = ImageStaffModel.get_all_images()
    filenames_db = set(img.get('filename') for img in images_db if img.get('filename'))
    
    # Fichiers physiques
    files_physical = set()
    if os.path.exists(destination_folder):
        files_physical = set(f for f in os.listdir(destination_folder) 
                           if os.path.isfile(os.path.join(destination_folder, f)) 
                           and not f.startswith('.'))
    
    # Images en DB mais pas sur le disque
    missing_files = filenames_db - files_physical
    
    # Fichiers sur le disque mais pas en DB
    orphan_files = files_physical - filenames_db
    
    # Affichage des résultats
    print(f"📊 Images en base de données : {len(images_db)}")
    print(f"📁 Fichiers physiques        : {len(files_physical)}")
    print()
    
    if missing_files:
        print(f"⚠️  {len(missing_files)} image(s) en DB mais fichier manquant :")
        for f in missing_files:
            print(f"   - {f}")
        print()
    
    if orphan_files:
        print(f"⚠️  {len(orphan_files)} fichier(s) orphelins (non référencés en DB) :")
        for f in orphan_files:
            print(f"   - {f}")
        print()
    
    if not missing_files and not orphan_files:
        print("✅ Tout est en ordre ! Base de données et fichiers sont synchronisés.")
    
    print("="*60 + "\n")
    
    return {
        "total_db": len(images_db),
        "total_files": len(files_physical),
        "missing_files": list(missing_files),
        "orphan_files": list(orphan_files),
        "is_synchronized": len(missing_files) == 0 and len(orphan_files) == 0
    }