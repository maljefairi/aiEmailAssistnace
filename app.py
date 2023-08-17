from flask import Flask, render_template, request, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Make sure to keep this a secret in production.

class SettingsForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    about_me = TextAreaField('About Me', validators=[DataRequired()])
    submit = SubmitField('Save Changes')

@app.route('/')
def dashboard():
    with open('emails.json', 'r') as f:
        emails = json.load(f)
    
    # For simplicity, considering all emails as new. You can adjust this based on your actual needs.
    new_emails = emails
    combined_data = [
        {
            "email": email,
            "reply": {"reply": "AI Generated Reply..."}  # Example reply data
        }
        for email in emails
    ]
    
    return render_template('dashboard.html', new_emails=new_emails, combined_data=combined_data)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    form = SettingsForm()
    if form.validate_on_submit():
        # Save the settings, for the demo I'm just printing them.
        print(form.name.data)
        print(form.about_me.data)
        # Redirect to dashboard after saving.
        return redirect(url_for('dashboard'))
    return render_template('settings.html', form=form, saved_ai_instructions="Sample saved AI instructions.")

@app.route('/generate_reply', methods=['POST'])
def generate_reply():
    selected_emails = request.form.getlist('selected_emails')
    action = request.form.get('action')
    if action == 'generate':
        # For demo purposes, just printing. You can integrate the OpenAI API here to generate replies.
        for email in selected_emails:
            print(f"Generated reply for email {email}")
    elif action == 'send':
        # For demo purposes, just printing. Here, you'd send the generated replies.
        for email in selected_emails:
            print(f"Sent reply for email {email}")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
