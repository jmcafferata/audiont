
from flask import Flask, flash, request, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import os
import config

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'users/'
app.config['APPLICATION_ROOT'] = '/'+config.bot_code



# Make sure to use a secret key for your application
app.secret_key = "your-secret-key"


# This code is used to upload a file to a user's folder. It is used in the vectorizar.html file to upload the file. It is also used in the app.py file to save the file in the user's folder.


@app.route(app.config['APPLICATION_ROOT'] + '/vectorizar/<user_id>', methods=['GET', 'POST'])
def upload_file(user_id):
    if request.method == 'POST':
        # Check if the file is present in the request
        if 'file' not in request.files:
            flash('No file found')
            return redirect(request.url)
        
        file = request.files['file']

        file_info = request.form.get('file_info')


        # cehck if file is pdf or txt
        if file.filename.split('.')[-1] not in ['pdf','txt']:
            return render_template('error.html', user_id=user_id)
        
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
        
        file.save(os.path.join(user_folder, filename))
        # take the user to listo.html (in the templates folder)
        

        #store the file name and file info in a txt file in the to_vectorize folder
        # the name of the txt file is the same as the name of the pdf file
        with open(os.path.join(user_folder, 'metadata_'+filename.split('.')[0]+'.txt'), 'w') as f:
            f.write(file_info)

    

        return render_template('listo.html', user_id=user_id)


    return render_template('vectorizar.html', user_id=user_id)



if __name__ == '__main__':
    app.run(debug=True)