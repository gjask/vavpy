from peewee import CharField, IntegerField, ForeignKeyField, DateTimeField,\
    BooleanField, PrimaryKeyField, Proxy, ReverseRelationDescriptor, fn
import datetime
import random
import string
import csv
from playhouse import db_url, flask_utils


# todo db.create_tables([], safe=True)

__all__ = ['Category', 'Entry', 'Contact', 'Contestant', 'Start', 'Check', 'db',
           'connect_manually', 'Result', 'Result_vloz']

_letters = string.ascii_letters + string.digits
db = flask_utils.FlaskDB()


def connect_manually(url, **kwargs):
    conn = db_url.connect(url, **kwargs)
    if isinstance(db.database, Proxy):
        db.database.initialize(conn)
    else:
        db.database = conn
    return db.database


def time2str(time_int):
    h, m, s = time_int // 3600, time_int % 3600 // 60, time_int % 60
    return '{:0>2}:{:0>2}:{:0>2}'.format(h, m, s)


def str2time(time_str):
    h, m, s = (int(n) for n in time_str.split(':'))
    return h * 3600 + m * 60 + s


def new_passcode():
    return ''.join(random.choice(_letters) for i in range(6))


first_start = str2time('09:30:00')  # todo move to database or setting
step = 30  # seconds
missing_numbers = []


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
        return '{}-{:0>4}'.format(self.created.strftime('%y'), self.id)

    @staticmethod
    def get_id(code):
        return int(code[-4:])


class Contestant(db.Model):
    name = CharField()
    category = ForeignKeyField(Category)
    entry = ForeignKeyField(Entry, 'contestants')

    def __unicode__(self):
        return self.name


class Gate(db.Model):
    number = IntegerField(unique=True, null=True)
    name = CharField(unique=True, null=True)
    note = CharField(null=True)

    @property
    def ident(self):
        return self.name or self.number


class Start(db.Model):
    number = PrimaryKeyField()
    contestant = ForeignKeyField(Contestant, 'starts', unique=True)
    # number = IntegerField(index=True, unique=True)  # sequence=
    # real_time = TimeField(null=True)
    real_time = IntegerField(null=True)
    disqualified = BooleanField(default=False)

    def __unicode__(self):
        return str(self.number)

    @property
    def time(self):
        return first_start + step * (self.number - 1)

    # @classmethod
    # def schedule_entry(cls, entry):
    #     source = (Contestant
    #               .select(Contestant.id)
    #               .where(Contestant.entry == entry)
    #               )
    #     cls.insert_from([cls.contestant], source).execute()

    @classmethod
    def schedule_contestants(cls, contestants):
        first = Start.select(fn.Max(Start.number) + 1).scalar()
        data = []
        delta = 0
        for n, contestant in enumerate(contestants):
            if n in missing_numbers:
                delta += 1
            data.append({'contestant': contestant, 'number': first + n + delta})
        cls.insert_many(data).execute()


class Check(db.Model):
    # gate = ForeignKeyField(Gate, 'checks')
    gate = IntegerField()
    line = IntegerField()
    number = ForeignKeyField(Start, 'checks')
    points = IntegerField(default=0)
    time = IntegerField(null=True)

    @classmethod
    def grouped_by_number(cls, category=None):
        res = {}  # todo defaultdict
        query = cls.select()

        for check in query:
            if check.number_id not in res:
                res[check.number_id] = {}
            res[check.number_id][check.gate] = check.points

        return res

    @classmethod
    def from_csv(cls, file, gate):
        _step = 100
        query_list = list(cls._query_from_csv(file, gate))
        for i in range(-(-len(query_list) // _step)):
            cls.insert_many(query_list[i * _step:(i + 1) * _step]).execute()

    @staticmethod
    def _query_from_csv(file, gate):
        # todo rewrite using dictcsvreader
        reader = csv.reader(file)
        for count, line in enumerate(reader):
            try:
                if len(line) >= 3:
                    time = str2time(line[2])
                else:
                    time = None
                yield {
                    'gate': gate,
                    'line': count,
                    'number': int(line[0]),
                    'points': int(line[1]),
                    'time': time
                }
            except (ValueError, IndexError):
                continue


class Result_vloz(db.Model):
    _view_name = 'result_vloz'
    _point_penalty = 120
    _final_gate = 5
    _gates = list(range(1, _final_gate + 1))

    number = ForeignKeyField(Start, 'results_vloz',
                             primary_key=True, db_column='number')
    sum_points = IntegerField(null=True)
    disqualified = BooleanField()
    clear_time = IntegerField(null=True)
    final_time = IntegerField(null=True)
    # gates = ReverseRelationDescriptor(Check.number)

    @property
    def gates(self):
        return Check.select().where(
            (Check.number == self.number) & (Check.gate << self._gates)
        )

    @classmethod
    def set_view(cls):
        create_sql = """
            create view {view} as
            select
                s.number, p.sum_points,
                (g.time is null or s.disqualified) as 'disqualified',
                g.time - s.real_time as 'clear_time',
                g.time - s.real_time + sum_points * {penalty} as 'final_time'
            from start s
            left join (
                select
                    number_id, time
                from 'check'
                where gate = {goal}
            ) g on s.number = g.number_id
            left join (
                select
                    number_id,
                    sum(points) as 'sum_points'
                from 'check'
                where gate in ({gates})
                group by number_id
            ) p on s.number = p.number_id
            order by disqualified asc, final_time asc;
        """.format(
            view=cls._view_name,
            penalty=cls._point_penalty,
            goal=cls._final_gate,
            gates=', '.join(str(g) for g in cls._gates)
        )

        with db.database.atomic():
            db.database.execute_sql('drop view if exists %s;' % cls._view_name)
            db.database.execute_sql(create_sql)


class Result(db.Model):
    _view_name = 'result'
    _point_penalty = 120
    _step = 120
    _final_gate = 8
    _gates = list(range(1, _final_gate + 1))

    number = ForeignKeyField(Start, 'result',
                             primary_key=True, db_column='number')
    points = IntegerField(null=True)
    disqualified = BooleanField()
    clear_time = IntegerField(null=True)
    sum_points = IntegerField(null=True)
    # gates = ReverseRelationDescriptor(Check.number)

    @property
    def gates(self):
        return Check.select().where(
            (Check.number == self.number) & (Check.gate << self._gates)
        )

    @classmethod
    def set_view(cls):
        create_sql = """
        create view {view} as
        select
            s.number, p.points,
            (g.time is null or s.disqualified) as 'disqualified',
            g.time - s.real_time as 'clear_time',
            (g.time - s.real_time - b.best) / {step} + p.points as 'sum_points'
        from start s
        left join (
            select
                number_id, time
            from 'check'
            where gate = {goal}
        ) g on s.number = g.number_id
        left join (
            select
                number_id,
                sum(points) as 'points'
            from 'check'
            where gate in ({gates})
            group by number_id
        ) p on s.number = p.number_id
        left join contestant c on c.id = s.contestant_id
        left join (
            select
                c.category_id,
                min(g.time - s.real_time) as 'best'
            from start s
            left join contestant c on s.contestant_id = c.id
            left join 'check' g on s.number = g.number_id
            where g.gate = {goal}
            group by c.category_id
        ) b on c.category_id = b.category_id
        order by disqualified asc, sum_points asc, p.points asc, clear_time asc;
    """.format(
            view=cls._view_name,
            penalty=cls._point_penalty,
            goal=cls._final_gate,
            gates=', '.join(str(g) for g in cls._gates),
            step=cls._step
        )

        with db.database.atomic():
            db.database.execute_sql('drop view if exists %s;' % cls._view_name)
            db.database.execute_sql(create_sql)
