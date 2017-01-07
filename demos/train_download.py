'''
Example how to download a pickled dataset from a url. 
'''
import donkey as dk


print('Downloading file, this could take some time.)
url = 'https://s3.amazonaws.com/donkey_resources/port.pkl'
X, Y = dk.datasets.load_url(url)

print('Loading Model.')
model = dk.models.cnn3_full1()

print('Fitting Model.')
model.fit(X,Y, nb_epoch=10, validation_split=0.2)


model.save('test_model')