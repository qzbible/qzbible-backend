# schemas/user_schema.py

from marshmallow import Schema, fields, validate, Email

class CreateAdminSchema(Schema):
    email = fields.Email(required=True)
    magasin_id = fields.Str(required=True)  # transmis sous forme de string

class SetPasswordSchema(Schema):
    token = fields.Str(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=6))



class ResetPasswordSchema(Schema):
    new_password = fields.String(required=False)