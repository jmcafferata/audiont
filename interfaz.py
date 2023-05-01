
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'users/'


# Make sure to use a secret key for your application
app.secret_key = "your-secret-key"


# This code is used to upload a file to a user's folder. It is used in the vectorizar.html file to upload the file. It is also used in the app.py file to save the file in the user's folder.


@app.route('/vectorizar/<user_id>', methods=['GET', 'POST'])
def upload_file(user_id):
    if request.method == 'POST':
        # Check if the file is present in the request
        if 'file' not in request.files:
            flash('No file found')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Check if the filename is empty
        if file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        # Save the file to the user's folder
        filename = secure_filename(file.filename)
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], user_id,"to_vectorize")
        # check if the user folder exists, if not create it
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)       
        # delete all files in the folder
        for xfile in os.listdir(user_folder):
            os.remove(os.path.join(user_folder, xfile))
        
        file.save(os.path.join(user_folder, filename))
        flash('File uploaded successfully')

    return render_template('vectorizar.html', user_id=user_id)



if __name__ == '__main__':
    app.run(debug=True)