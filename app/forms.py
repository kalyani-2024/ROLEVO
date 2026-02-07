from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, TextAreaField, SubmitField, HiddenField
from wtforms.validators import DataRequired

class PostForm(FlaskForm):
    post = TextAreaField(('Your response'), validators=[DataRequired()])
    submit = SubmitField(('Submit'))

class AdminForm(FlaskForm):
    id = HiddenField(('ID'))
    name = StringField(('Name'), validators=[DataRequired()])
    scenario = TextAreaField(('Scenario'), validators=[DataRequired()])
    person_name = StringField(('Person Name'), validators=[DataRequired()])
    roleplay_file = FileField(('Roleplay File'), validators=[DataRequired()])
    image_file = FileField(('Image File'), validators=[DataRequired()])
    comp_file = FileField(('Competency File(Only if update needed)'))
    submit = SubmitField('Submit')