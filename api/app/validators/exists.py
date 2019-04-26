from voluptuous import Invalid


class Exist:
    """Verifies against the database an entity exist or not in the database"""
    def __init__(self, model, field, reversed=False, msg=None):
        self.model = model
        self.field = field
        self.reversed = reversed
        self.msg = msg

    def __call__(self, v):
        filters = {self.field: v}
        query = self.model.query.filter_by(**filters).first()
        if query is not None and self.reversed is False:
            raise Invalid(self.msg or "already exists in the database")
        if query is None and self.reversed is True:
            raise Invalid(self.msg or "doesn't exists in the database")
        return v


class DoesntExist(Exist):
    """Verifies against the database an entity doesn't exist in the database"""
    def __init__(self, model, field, reversed=True, msg=None):
        Exist.__init__(self, model, field, reversed=reversed, msg=msg)

    def __call__(self, v):
        Exist.__call__(self, v=v)
