# utils/email.py
import smtplib
from email.mime.text import MIMEText
from flask import current_app
from jinja2 import TemplateNotFound
from flask import render_template
from email.mime.multipart import MIMEMultipart


def send_validation_email(to_email, token):
    link = f"http://localhost:5173/resetpassword/{token}"
    body = f"""
    Bonjour 👋,

    Votre compte a été créé. Veuillez cliquer sur le lien ci-dessous pour définir votre mot de passe :

    {link}

    Ce lien expire dans 24h.

    L’équipe de la plateforme.
    """
    msg = MIMEText(body)
    msg["Subject"] = "Reinitialisation de mot de passe"
    msg["From"] = current_app.config["MAIL_SENDER"]
    msg["To"] = to_email

    try:
        with smtplib.SMTP(current_app.config["EMAIL_HOST"], current_app.config["EMAIL_PORT"]) as server:
            if current_app.config["EMAIL_USE_TLS"]:
                server.starttls()
            server.login(current_app.config["EMAIL_HOST_USER"], current_app.config["EMAIL_HOST_PASSWORD"])
            server.send_message(msg)
            print("✅ Email envoyé à", to_email)
    except Exception as e:
        print("❌ Erreur d'envoi de mail :", e)
        
        
#  Fonction pour envoyer un email de création de compte  
def send_validation_email_creation_account(to_email, credentials):
    #print("Envoi de l'email de création de compte à", to_email, "debuté.")
    try:
        html_content = render_template(
            "email/account_creation_email.html",
            first_name=credentials['first_name'],
            role=credentials['role'],
            email=credentials['email'],
            password=credentials['password']
        )
    except TemplateNotFound as e:
        print("❌ Template non trouvé :", e)
        return
    except Exception as e:
        print("❌ Erreur de rendu du template :", e)
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Création de votre compte"
    msg["From"] = current_app.config["MAIL_SENDER"]
    msg["To"] = to_email
    
    # Version texte (fallback si HTML pas supporté)
    plain_text = f"""
    Bonjour {credentials['first_name']} 👋,

    Votre compte {credentials['role']} a été créé. Veuillez utiliser les identifiants suivants pour vous connecter :
    Email : {credentials['email']}
    Mot de passe : {credentials['password']}

    L’équipe de la plateforme.
    """
    
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))
    #print("Contenu HTML de l'email de création de compte :", html_content)
    #print("Envoi de l'email de création de compte à", to_email, "procédé.")
    try:
        with smtplib.SMTP(current_app.config["EMAIL_HOST"], current_app.config["EMAIL_PORT"]) as server:
            if current_app.config["EMAIL_USE_TLS"]:
                server.starttls()
            server.login(current_app.config["EMAIL_HOST_USER"], current_app.config["EMAIL_HOST_PASSWORD"])
            server.send_message(msg)
            print("✅ Email envoyé à", to_email)
    except Exception as e:
        print("❌ Erreur d'envoi de mail :", e)

import random

def generer_otp(longueur=6):
    """
    Génère un OTP numérique de la longueur spécifiée.
    
    Args:
        longueur (int): Nombre de chiffres de l'OTP (par défaut 6)
    
    Returns:
        str: OTP généré
    """
    otp = ''.join([str(random.randint(0, 9)) for _ in range(longueur)])
    return otp
      
#  Fonction pour envoyer un email de création de compte  
def send_otp_mail(to_email, code_auth):
    #print("Envoi de l'email de création de compte à", to_email, "debuté.")
    try:
        html_content = render_template(
            "otp/2FA-auth-fr.html",
            code_auth= code_auth
        )
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Code d'authentification"
        msg["From"] = current_app.config["MAIL_SENDER"]
        msg["To"] = to_email
        print('email and code', to_email, code_auth )
        # Version texte (fallback si HTML pas supporté)
        plain_text = f"""
        Bonjour  👋,

        Votre code d'authentification est : {code_auth}
        
        L’équipe de la plateforme.
        """
        
        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_content, "html"))
        with smtplib.SMTP(current_app.config["EMAIL_HOST"], current_app.config["EMAIL_PORT"]) as server:
            if current_app.config["EMAIL_USE_TLS"]:
                server.starttls()
            server.login(current_app.config["EMAIL_HOST_USER"], current_app.config["EMAIL_HOST_PASSWORD"])
            server.send_message(msg)
            print("✅ Email envoyé à", to_email)
        return True
    except TemplateNotFound as e:
        print("❌ Template non trouvé :", e)
        return False
    except Exception as e:
        print("❌ Erreur de rendu du template :", e)
        return False
     


# Fonction pour envoyer un email de réinitialisation de mot de passe
def send_reset_password_email(to_email, token):
    reset_link = f"http://localhost:5173/resetpassword/{token}"
    subject = "Réinitialisation de mot de passe"
    try: 
        html_content = render_template(
            "email/reset_password_email.html",
            token=token
        )
    except TemplateNotFound as e:
        print("❌ Template non trouvé :", e)
        return
    except Exception as e:
        print("❌ Erreur de rendu du template :", e)
        return
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = current_app.config["MAIL_SENDER"]
    msg["To"] = to_email
    
    # Fallback en texte brut si le HTML n'est pas supporté
    plain_text = f"""
    Bonjour,

    Cliquez sur le lien suivant pour réinitialiser votre mot de passe :
    {reset_link}

    Ce lien est valide pour 30 minutes.
    """

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))
    try:
        with smtplib.SMTP(current_app.config["EMAIL_HOST"], current_app.config["EMAIL_PORT"]) as server:
            if current_app.config["EMAIL_USE_TLS"]:
                server.starttls()
            server.login(current_app.config["EMAIL_HOST_USER"], current_app.config["EMAIL_HOST_PASSWORD"])
            server.send_message(msg)
            print("✅ Email de réinitialisation envoyé à", to_email)
    except Exception as e:
        print("❌ Erreur d'envoi de mail :", e)


