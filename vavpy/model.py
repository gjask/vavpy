from peewee import Model, CharField, IntegerField, ForeignKeyField,\
    DateTimeField, BooleanField, TimeField, PrimaryKeyField
import datetime
import random
import string
import csv
from playhouse import db_url, flask_utils


first_start = datetime.time(9, 30)  # todo move to database or setting
step = datetime.timedelta(seconds=30)


# __all__ = []
__all__ = ['Category', 'Entry', 'Contact', 'Contestant', 'Start', 'Check', 'db']

_letters = string.ascii_letters + string.digits
# db = db_url.connect('sqlite:///test.db')
db = flask_utils.FlaskDB()


def dt_add(time, delta):
    realtime = datetime.datetime.combine(datetime.date.today(), time)
    realtime += delta
    return realtime.time()


def new_passcode():
    return ''.join(ch for ch in random.choice(_letters))


# class BaseModel(Model):
#     class Meta:
#         database = db
#
#     # def __new__(cls, *args, **kwargs):
#     #     super(BaseModel, cls).__new__(cls, *args, **kwargs)
#     #     __all__.append(cls.__name__)


class Category(db.Model):
    name = CharField()

    def __unicode__(self):
        return self.name


class Contact(db.Model):
    club = CharField(null=True)
    address = CharField(null=True)
    city = CharField(null=True)
    psc = CharField(null=True)
    country = CharField(null=True)
    phone = CharField()
    email = CharField()


class Entry(db.Model):
    # code = CharField()
    created = DateTimeField(default=datetime.datetime.now)
    pass_code = CharField(default=new_passcode)
    contact = ForeignKeyField(Contact)

    @property
    def code(self):
        return '{}{:0>4}'.format(self.created.strftime('%y'), self.id)

    @staticmethod
    def get_id(code):
        return int(code[2:])


class Contestant(db.Model):
    name = CharField()
    category = ForeignKeyField(Category)
    entry = ForeignKeyField(Entry, 'contestants')


class Start(db.Model):
    number = PrimaryKeyField()
    contestant = ForeignKeyField(Contestant, 'starts', unique=True)
    # number = IntegerField(index=True, unique=True)  # sequence=
    real_time = TimeField(null=True)
    disqualified = BooleanField(default=False)

    @property
    def time(self):
        return dt_add(first_start, step * (self.number - 1))

    # @classmethod
    # def schedule_entry(cls, entry):
    #     source = (Contestant
    #               .select(Contestant.id)
    #               .where(Contestant.entry == entry)
    #               )
    #     cls.insert_from([cls.contestant], source).execute()

    @classmethod
    def schedule_contestants(cls, contestants):
        cls.insert_many({'contestant': c} for c in contestants).execute()


# class Time(db.Model):
#     gate = IntegerField()
#     line = IntegerField()
#     # number = ForeignKeyField()
#     number = IntegerField()
#     time = DateTimeField()


# select start.number, contestant.*, sum(check.points) as points_sum, max(check.time) - start.time as bare_time, points_sum * 2min + bare_time as final_time from check left join by start left join by contstant group by start.number order by final_time asc;


class Check(db.Model):
    gate = IntegerField()
    line = IntegerField()
    number = ForeignKeyField(Start, 'checks')
    points = IntegerField(default=0)
    time = DateTimeField(null=True)

    @classmethod
    def from_csv(cls, file, gate):
        cls.insert_many(cls._query_from_csv(file, gate)).execute()

    @staticmethod
    def _query_from_csv(file, gate):
        reader = csv.reader(file)
        for count, line in enumerate(reader):
            try:
                yield {
                    'gate': gate,
                    'line': count,
                    'number': int(line[0]),
                    'points': int(line[1])
                }
            except (ValueError, IndexError):
                continue

