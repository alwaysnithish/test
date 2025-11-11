from django import forms

class FileUploadForm(forms.Form):
    file = forms.FileField(label='Choose a file')
    convert_to = forms.ChoiceField(choices=[
        ('pdf', 'PDF'),
        ('txt', 'Text'),
        ('docx', 'Word (.docx)')
    ])