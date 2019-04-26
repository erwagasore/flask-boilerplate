from app.extensions import db
from app.awaremodel import AwareModel


class RevokedToken(AwareModel):
    """
    Representing revoked tokens in relationship with the user

    |-----------------------------------+------|
    | token                             | user |
    |-----------------------------------+------|
    | eyJhbGciOiJub25lIn0.eyJpZCI6FoO0. | bar  |
    |-----------------------------------+------|
    """
    token = db.Column(db.String, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship(
        'User', primaryjoin='User.id == RevokedToken.user_id',
        backref=db.backref('revoked', uselist=False, cascade='all, delete-orphan'))

    @staticmethod
    def get_revoked(user):
        return RevokedToken.query.filter_by(user_id=user.id).all()
