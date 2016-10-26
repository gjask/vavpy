# from flask_wtf import Form
from wtforms import Form
from wtforms import FormField, FieldList, StringField, SubmitField, \
    IntegerField, SelectField, HiddenField, validators, FileField, TextAreaField
from wtforms.widgets import HiddenInput
from wtfpeewee.orm import model_form, ModelConverter, PrimaryKeyField

from vavpy.model import Contact, Contestant, Category

# class SelfAwareForm(Form):
#     def is_submitted(self):
#         # todo


# class ContestantForm(Form):
#     id = IntegerField()  # widget=HiddenInput())
#     name = StringField(validators=[validators.DataRequired()])
#     category = SelectField(validators=[validators.DataRequired()], choices=[])
#
#     # def __init__(self, *args, **kwargs):
#     #     cats = Category.select()
#     #     self.category.choices = [(cat.name, cat.name) for cat in cats]
#     #     super(ContestantForm, self).__init__(*args, **kwargs)


def handle_pk(model, field, **kwargs):
    return field.name, HiddenField()


inline_converter = ModelConverter({PrimaryKeyField: handle_pk})


ContestantForm = model_form(
    Contestant,
    exclude=['entry'],
    allow_pk=True,
    converter=inline_converter
)
ContactForm = model_form(Contact)


class NewEntryForm(Form):
    contact = FormField(ContactForm)
    contestants = FieldList(FormField(ContestantForm), min_entries=1)
    save = SubmitField('Save')
    paste = SubmitField('Save and Add')


class FromCodeEntryForm(Form):
    code = StringField(validators=[validators.DataRequired()])
    paste = SubmitField('Add')


class PrintStartListForm(Form):
    from_page = SelectField(coerce=int)
    to_page = SelectField(coerce=int)
    print_list = SubmitField('Print Start List')

    def set_values(self, page_count, fpage, tpage):
        choices = [(x, str(x)) for x in range(1, page_count + 1)]
        self.from_page.choices = choices
        self.to_page.choices = choices
        if not self.from_page.data or not self.to_page.data:
            self.from_page.data = fpage
            self.to_page.data = tpage


class UploadCheckForm(Form):
    check_number = IntegerField(validators=[validators.DataRequired()])
    table = FileField()  # validators=[validators.DataRequired()])
    upload = SubmitField()


class SQLForm(Form):
    query = TextAreaField(validators=[validators.DataRequired()])
    execute = SubmitField()
