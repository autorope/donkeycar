#!flask/bin/python

from flask import Flask, jsonify, request, redirect
import os
import json
import uuid
from keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img


app = Flask(__name__)
app.config['DEBUG'] = True



cwd = os.getcwd()

tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol', 
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web', 
        'done': False
    }
]

@app.route('/todo/api/v1.0/tasks', methods=['GET'])
def get_tasks():
    return jsonify({'tasks': tasks})

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            print(request)
            return redirect(request.url)

        datagen = ImageDataGenerator(
                rotation_range=40,
                width_shift_range=0.2,
                height_shift_range=0.2,
                rescale=1./255,
                shear_range=0.2,
                zoom_range=0.2,
                horizontal_flip=True,
                fill_mode='nearest')


        file = request.files['file']
        extension = os.path.splitext(file.filename)[1]
        f_name = str(uuid.uuid4()) + extension
        f_path = os.path.join(cwd, f_name)
        file.save(f_path)
        img = load_img(f_path)
        x = img_to_array(img)
        x = x.reshape((1,) + x.shape)

        i = 0
        for batch in datagen.flow(x, batch_size=1,
                                  save_to_dir='preview', save_prefix='cat', save_format='jpeg'):
            i += 1
            if i > 20:
                break  # otherwise the generator would loop indefinitely

        print(x)
        return json.dumps({'filename':f_name})
        

    if request.method == 'GET':
        return "works"


if __name__ == '__main__':
    app.secret_key = 'many random bytes'
    app.run(debug=True)
