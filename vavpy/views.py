from flask import Flask, render_template, abort, request, redirect, url_for,\
    flash, Response
from playhouse.flask_utils import get_object_or_404
from peewee import fn, JOIN
import io
import csv

from vavpy.forms import *
from .model import *
from .model import time2str


app = Flask(__name__)
app.secret_key = 'SOME_BULLSHIT'
app.config['DATABASE'] = 'sqlite:///test.db'

db.init_app(app)


_page_size = 30


@app.template_filter('time')
def time2str_filter(time):
    try:
        return time2str(time)
    except TypeError:
        return ''


@app.route('/', methods=('GET', 'POST'))
def dashboard_view():
    start_list = Start.select().order_by(Start.number.desc())
    checkpoints = Check.select(Check.gate, fn.Count(Check.id).alias('count'))\
        .group_by(Check.gate)

    check_form = UploadCheckForm(request.form)
    code_form = FromCodeEntryForm(request.form)
    print_form = PrintStartListForm(request.form)
    print_form.set_values(
        -(-len(start_list) // _page_size),
        1,
        len(start_list) // _page_size
    )

    # Upload checkpoint table
    if request.method == 'POST' and check_form.validate():
        file = request.files[check_form.table.name]
        Check.delete()\
            .where(Check.gate == check_form.check_number.data)\
            .execute()
        stream = io.TextIOWrapper(file.stream)
        Check.from_csv(stream, check_form.check_number.data)
        flash('Checkpoint data uploaded successfully')
        return redirect(url_for('dashboard_view'))

    # Add entry from pre-registration
    if request.method == 'POST' and code_form.validate():
        entry_id = Entry.get_id(code_form.code.data)
        return redirect(url_for('edit_entry_view', entry_id=entry_id))

    # Print start list
    if request.method == 'POST' and print_form.validate():
        return redirect(url_for(
            'start_list_view',
            from_n=_page_size * (print_form.from_page.data - 1) + 1,
            to_n=_page_size * print_form.to_page.data
        ))

    return render_template(
        'dashboard.html',
        categories=Category.select(),
        start_list=start_list,
        pass_code_form=code_form,
        print_form=print_form,
        check_form=check_form,
        checkpoints=checkpoints
    )


@app.route('/entry/new', methods=('GET', 'POST'))
@app.route('/entry/<int:entry_id>/edit', methods=('GET', 'POST'))
def edit_entry_view(entry_id=None):
    # consider using db.atomic() or db.transaction()

    if entry_id is not None:
        entry = get_object_or_404(Entry, (Entry.id == entry_id))
        form = NewEntryForm(request.form, entry)
    else:
        entry = Entry()
        entry.contact = Contact()
        form = NewEntryForm(request.form)

    if request.method == 'POST' and form.validate():
        form.contact.form.populate_obj(entry.contact)
        entry.contact.save()
        entry.save()

        # todo delete contestant (or disable from scheduling)
        contestants = []
        for cnt_formfield in form.contestants:
            if cnt_formfield.form.id.data:
                cnt = Contestant.get(id=cnt_formfield.form.id.data)
            else:
                cnt_formfield.form.id.data = None
                cnt = Contestant()  # todo maybe optimize
                cnt.entry = entry
            cnt_formfield.form.populate_obj(cnt)
            cnt.save()
            contestants.append(cnt)

        if form.paste.data:
            Start.schedule_contestants(contestants)

        return redirect(url_for('list_entry_view', entry_id=entry.id))
    else:
        return render_template('entry_edit.html', form=form)


@app.route('/entry/<int:entry_id>')
def list_entry_view(entry_id):
    entry = get_object_or_404(Entry, (Entry.id == entry_id))
    return render_template('entry_list.html', entry=entry)


@app.route('/start')
@app.route('/start/<int:from_n>')
@app.route('/start/<int:from_n>-<int:to_n>')
def start_list_view(from_n=None, to_n=None):
    start_list = Start.select()
    if from_n is not None:
        start_list = start_list.offset(from_n - 1)
    if to_n is not None:
        start_list = start_list.limit(to_n - from_n + 1)
    return render_template('start_list.html', start_list=start_list)


@app.route('/results-inner/<category_name>')
@app.route('/results-inner/<category_name>/<csv_export>')
def results_view(category_name=None, csv_export=False):
    _final_gate = 5
    _point_penalty = 120
    _gates = 1, 2, 3, 4, 5
    category = get_object_or_404(Category, (Category.name == category_name))

    csv_headers = ['order', 'number', 'name', 'club', 'disqualified',
                   'sum_points', 'clear_time', 'final_time']

    # todo redo as views, so you can easily find disqualified

    results = Start.raw("""
        select
            s.number, c.name, a.club, p.sum_points,
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
        left join contestant c on c.id = s.contestant_id
        left join category k on c.category_id = k.id
        left join entry e on e.id = c.entry_id
        left join contact a on a.id = e.id
        where c.category_id == {category}
        order by disqualified asc, final_time asc;
    """.format(
        penalty=_point_penalty,
        goal=_final_gate,
        gates=', '.join(str(g) for g in _gates),
        category=category.id
    )).dicts()

    if csv_export:
        file = 'vysledky_vloz_{}.csv'.format(category_name)
        stream = io.StringIO()
        writer = csv.DictWriter(stream, csv_headers)
        writer.writeheader()

        for order, line in enumerate(results.dicts(), 1):
            line['order'] = order
            line['clear_time'] = time2str(line['clear_time'] or 0)
            writer.writerow(line)

        stream.seek(0)
        resp = Response(stream, content_type='text/csv')
        resp.headers['Content-Disposition'] = "attachment; filename=%s" % file
        return resp

    return render_template(
        'results.html',
        results=enumerate(results),
        category=category_name
    )


@app.route('/results-outer/<category_name>')
@app.route('/results-outer/<category_name>/<csv_export>')
def results_outer_view(category_name=None, csv_export=False):
    _final_gate = 8
    _point_penalty = 120
    _gates = 1, 2, 3, 4, 5, 6, 7, 8
    _step = 120
    category = get_object_or_404(Category, (Category.name == category_name))

    csv_headers = ['order', 'number', 'name', 'club', 'points', 'disqualified',
                   'clear_time', 'sum_points']

    best_time = Start.raw("""
        select
            min(g.time - s.real_time) as 'best_time'
        from start s
        left join 'check' g on s.number = g.number_id
        left join contestant c on c.id = s.contestant_id
        where g.gate = {goal} and c.category_id = {category};
    """.format(
        goal=_final_gate,
        category=category.id
    )).scalar()

    results = Start.raw("""
        select
            s.number, c.name, a.club, p.points,
            (g.time is null or s.disqualified) as 'disqualified',
            g.time - s.real_time as 'clear_time',
            (g.time - s.real_time - {best}) / {step} + p.points as 'sum_points'
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
        left join category k on c.category_id = k.id
        left join entry e on e.id = c.entry_id
        left join contact a on a.id = e.id
        where c.category_id == {category}
        order by disqualified asc, sum_points asc, p.points asc, clear_time asc;
    """.format(
        penalty=_point_penalty,
        goal=_final_gate,
        gates=', '.join(str(g) for g in _gates),
        category=category.id,
        step=_step,
        best=best_time
    ))

    if csv_export:
        file = 'vysledky_{}.csv'.format(category_name)
        stream = io.StringIO()
        writer = csv.DictWriter(stream, csv_headers)
        writer.writeheader()

        for order, line in enumerate(results.dicts(), 1):
            line['order'] = order
            line['clear_time'] = time2str(line['clear_time'] or 0)
            writer.writerow(line)

        stream.seek(0)
        resp = Response(stream, content_type='text/csv')
        resp.headers['Content-Disposition'] = "attachment; filename=%s" % file
        return resp

    return render_template(
        'results_outer.html',
        results=enumerate(results.dicts()),
        category=category_name
    )


@app.route('/contestant/<int:contestant_id>')
def contestant_view(contestant_id):
    pass


@app.route('/broken')
def broken_records_view():
    pass


# @app.route('/sql', methods=('GET', 'POST'))
# def sql_view():
#     form = SQLForm(request.form)
#     if request.method == 'POST' and form.validate():
#         result Entry.raw()
#     return render_template('sql.html')
