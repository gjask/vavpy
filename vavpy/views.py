from flask import Flask, render_template, abort, request, redirect, url_for,\
    flash

from vavpy.forms import *
from .model import *


app = Flask(__name__)
app.secret_key = 'SOME_BULLSHIT'


# @app.template_global()
# def isrecursive(field):
#     return isinstance(field, (Form, FieldList))
#
#
# @app.template_global()
# def isformfield(field):
#     return isinstance(field, FormField)


# def populate_objects(formset, obj):
#     pass


@app.route('/', methods=('GET', 'POST'))
def dashboard_view():
    start_list = Start.select().order_by(Start.number)
    code_form = FromCodeEntryForm(request.form)

    if request.method == 'POST' and code_form.validate():
        code = code_form.pass_code.data
        try:
            entry = Entry.get(pass_code=code)  # todo, fix this bullshit
        except Entry.DoesNotExist:
            flash('Entry with code %s does not found!' % code)
        else:
            return redirect(url_for('edit_entry_view', entry_id=entry.id))

    return render_template(
        'dashboard.html',
        start_list=start_list,
        pass_code_form=code_form
    )


@app.route('/entry/new', methods=('GET', 'POST'))
@app.route('/entry/<int:entry_id>/edit', methods=('GET', 'POST'))
def edit_entry_view(entry_id=None):
    # consider using db.atomic() or db.transaction()

    if entry_id is not None:
        try:
            entry = Entry.get(id=entry_id)
        except Entry.DoesNotExist:
            abort(404)
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
    try:
        entry = Entry.get(id=entry_id)
    except Entry.DoesNotExist:
        abort(404)

    return render_template('entry_list.html', entry=entry)

