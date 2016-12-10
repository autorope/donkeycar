import os
import sys
import requests

print(sys.version)

image_dir = os.getcwd()

path = image_dir + '/donkey.jpg'


if __name__ == "__main__":
    

    url = 'http://localhost:5000/upload'
    files = {'file': open(path, 'rb')}
    r = requests.post(url, files=files)
    #response = requests.get(url)
    print(r.text)