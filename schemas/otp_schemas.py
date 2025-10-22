from marshmallow import Schema, fields, validate, validates, ValidationError

class SendOTPSchema(Schema):
    """Schéma pour l'envoi d'OTP"""
    email = fields.Email(
        required=True,
        error_messages={
            'required': 'Email requis',
            'invalid': 'Format d\'email invalide'
        }
    )

class VerifyOTPSchema(Schema):
    """Schéma pour la vérification d'OTP"""
    email = fields.Email(
        required=True,
        error_messages={
            'required': 'Email requis',
            'invalid': 'Format d\'email invalide'
        }
    )
    code = fields.String(
        required=True,
        validate=validate.Length(equal=6),
        error_messages={
            'required': 'Code OTP requis',
            'invalid': 'Le code doit contenir exactement 6 caractères'
        }
    )
    
    @validates('code')
    def validate_code(self, value):
        """Valide que le code contient uniquement des chiffres"""
        if not value.isdigit():
            raise ValidationError('Le code doit contenir uniquement des chiffres')

class ResendOTPSchema(Schema):
    """Schéma pour le renvoi d'OTP"""
    email = fields.Email(
        required=True,
        error_messages={
            'required': 'Email requis',
            'invalid': 'Format d\'email invalide'
        }
    )