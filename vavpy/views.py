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
app.config['DATABASE'] = 'sqlite:///test.db1'

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

    search_form = SearchForm(request.form)
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
        search_form=search_form,
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
    category = get_object_or_404(Category, (Category.name == category_name))
    results = (
        Result_vloz.select(
            Start.number, Contestant.name, Contact.club,
            Result_vloz.disqualified, Result_vloz.sum_points,
            Result_vloz.clear_time, Result_vloz.final_time
        )
        .join(Start)
        .join(Contestant)
        .join(Entry)
        .join(Contact)
        .where(Contestant.category == category)
    )
    checks = Check.grouped_by_number()

    csv_headers = ['order', 'number', 'name', 'club', 'disqualified',
                   'sum_points', 'clear_time', 'final_time']

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
        results=enumerate(results.dicts()),
        category=category_name
    )


@app.route('/results-outer/<category_name>')
@app.route('/results-outer/<category_name>/<csv_export>')
def results_outer_view(category_name=None, csv_export=False):
    category = get_object_or_404(Category, (Category.name == category_name))
    results = (
        Result.select(
            Start.number, Contestant.name, Contact.club, Result.points,
            Result.disqualified, Result.clear_time, Result.sum_points
        )
        .join(Start)
        .join(Contestant)
        .join(Entry)
        .join(Contact)
        .where(Contestant.category == category)
    )
    checks = Check.grouped_by_number()

    csv_headers = ['order', 'number', 'name', 'club', 'points', 'disqualified',
                   'clear_time', 'sum_points']

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
        checks=checks,
        category=category_name
    )


@app.route('/contestant/<int:contestant_id>')
def contestant_view(contestant_id):
    contestant = get_object_or_404(Contestant, (Contestant.id == contestant_id))
    checks = Check.select().where()
    return render_template('contestant.html')


@app.route('/broken')
def broken_records_view():
    pass


@app.route('/search', methods=('GET', 'POST'))
def search_view(keyword=None):
    form = SearchForm(request.form)
    query = None

    if request.method == 'POST' and form.validate():
        kw = '%' + form.keyword.data + '%'
        contition = (
            (Contestant.name ** kw)
            | (Contact.club ** kw)
            | (Contact.email ** kw)
        )

        try:
            number = int(kw)
        except (ValueError, TypeError):
            pass
        else:
            contition |= (Start.number == number)

        query = (
            Start.select(Start, Contestant, Contact)
            .join(Contestant)
            .join(Entry)
            .join(Contact)
            .where(contition)
        )

    return render_template('search.html', form=form, search=query)


# @app.route('/sql', methods=('GET', 'POST'))
# def sql_view():
#     form = SQLForm(request.form)
#     if request.method == 'POST' and form.validate():
#         result Entry.raw()
#     return render_template('sql.html')
