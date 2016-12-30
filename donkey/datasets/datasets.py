from os.path import dirname, realpath 
import os
import PIL

imgs_dir = dirname(dirname(realpath(__file__))+'/imgs/')
print(os.listdir(imgs_dir))


image_datasets = ['sidewalk']


def load_file_paths(dataset_name):
    if dataset_name in image_datasets:
        dataset_dir = os.path.join(imgs_dir, dataset_name)
        files = os.listdir(dataset_dir)
        file_paths = [os.path.join(dataset_dir, i) for i in files]
        return file_paths
    else:
        raise ValueError('The dataset: %s, is not availible.' %dataset_name)
