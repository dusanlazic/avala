from peewee import Model, DatabaseProxy

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db
