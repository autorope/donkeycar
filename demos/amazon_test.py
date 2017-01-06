import donkey as dk

datasets = {'moving_square_3000_frames': dk.datasets.moving_square(100, return_y=False)}

models = {
            'cnn3_full1_rnn1': dk.models.cnn3_full1_rnn1(),
            'cnn3_full1': dk.models.cnn3_full1(),
            'norm_cnn3_full1': dk.models.norm_cnn3_full1(),
            'cnn1_full1': dk.models.cnn1_full1(),
        }


results = []

for ds_name, ds in datasets.items():
    for m_name, m in models.items(): 
        m.compile(optimizer='adam', loss='mean_squared_error')
        X, Y = ds
        X_train, Y_train, X_test, Y_test = dk.utils.split_data(X, Y)
        hist = m.fit(X_train, Y_train, batch_size=32, nb_epoch=5, 
                         validation_data=(X_test, Y_test))
        
        result = {'model_name': m_name, 'dataset_name': ds_name, 
                  'min_val_loss': min(hist.history['val_loss'])
                 }
        results.append(result)
print(results)