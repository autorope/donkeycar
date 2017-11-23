
# coding: utf-8

# ## MXNet Pilot for Donkey car with early stopping and lr decay
# 
# @author: Sunil Mallya
# @author: Keji Xu


import mxnet as mx
import os
import numpy as np
import logging
from PIL import Image
from collections import namedtuple
Batch = namedtuple('Batch', ['data'])


head = '%(asctime)-15s %(message)s'
logging.basicConfig(level=logging.INFO, format=head)
    
class MXNetPilot():

    def load(self, model_path):
        f_params_file = model_path + "-best.params"
        f_symbol_file = model_path + "-symbol.json"
        sym, arg_params, aux_params = load_model(f_symbol_file, f_params_file)
        self.model = mx.mod.Module(symbol=sym, label_names=None)
        self.model.bind(for_training=False, data_shapes=[('data', (1, 3, 120, 160))])
        self.model.set_params(arg_params, aux_params, allow_missing=True)

    def train(self, train_iter, val_iter, 
              saved_model_path, num_epoch=100, steps=100, train_split=0.8,
              verbose=1, min_delta=.0005, patience=5, use_early_stop=True):

        save_best_model = EvalCallback(model_prefix=saved_model_path, op="min", save_model=True)


        self.model.bind(data_shapes=train_iter.provide_data, label_shapes=train_iter.provide_label)
        self.model.init_params(mx.init.Xavier(factor_type="in", magnitude=2.34))
        lr_sch = mx.lr_scheduler.FactorScheduler(step=1000, factor=0.99)
        self.model.init_optimizer(optimizer='adam', optimizer_params=(('learning_rate', 1E-2), ('lr_scheduler', lr_sch)))
        eval_metric = MAECustom()

        hist = self.model.fit(train_data=train_iter, 
                eval_data=val_iter, 
                eval_metric=eval_metric, 
                num_epoch=num_epoch,
                eval_end_callback=save_best_model,
                #epoch_end_callback=mx.callback.Speedometer(batch_size, 100),
               )
        return hist

    def get_train_val_iter(self, train_df, val_df, batch_size):
        train_iter = getIter(train_df, batch_size)
        val_iter = getIter(val_df, batch_size)

        return train_iter, val_iter

def getIter(df, batch):
    images = []
    a_labels = []
    t_labels = []

    for index, row in df.iterrows():
        img = np.array(Image.open(row['cam/image_array'])) #.resize((120, 160), Image.BILINEAR))
        img = np.swapaxes(img, 0, 2)
        img = np.swapaxes(img, 1, 2)
        images.append(img)
        a_labels.append(row['user/angle'])
        t_labels.append(row['user/throttle'])

    np_images = np.stack(images)    
    a_labels = np.stack(a_labels)
    t_labels = np.stack(t_labels)

    return mx.io.NDArrayIter({'data': np_images}, {'angle': a_labels, 'throttle': t_labels}, batch_size=batch)

def load_model(s_fname, p_fname):
    """
    Load model checkpoint from file.
    :return: (arg_params, aux_params)
    arg_params : dict of str to NDArray
        Model parameter, dict of name to NDArray of net's weights.
    aux_params : dict of str to NDArray
        Model parameter, dict of name to NDArray of net's auxiliary states.
    """
    symbol = mx.symbol.load(s_fname)
    save_dict = mx.nd.load(p_fname)
    arg_params = {}
    aux_params = {}
    for k, v in save_dict.items():
        tp, name = k.split(':', 1)
        if tp == 'arg':
            arg_params[name] = v
        if tp == 'aux':
            aux_params[name] = v
    return symbol, arg_params, aux_params


class MxnetLinear(MXNetPilot):
    def __init__(self, model=None, num_outputs=None, *args, **kwargs):
        super(MxnetLinear, self).__init__(*args, **kwargs)
        if model:
            self.model = model
        else:
            self.model = default_mxnet_linear()
    def run(self, img_arr):
        print(img_arr.shape)
        img_arr = np.swapaxes(img_arr, 0, 2)
        img_arr = np.swapaxes(img_arr, 1, 2)
        img_arr = img_arr.reshape((1,) + img_arr.shape)
        self.model.forward(Batch([mx.nd.array(img_arr)]))
        outputs = self.model.get_outputs()
        #print(len(outputs), outputs)
        steering = outputs[0].asnumpy()
        throttle = outputs[1].asnumpy()

        return steering[0][0], throttle[0][0]
        
def default_mxnet_linear(ctx=[mx.gpu(0)]):
   
    # Experiment with other network architectures
    
    data = mx.symbol.Variable(name="data")
    target = mx.symbol.Variable('angle')
    target2 = mx.symbol.Variable('throttle')

    body = mx.sym.Convolution(data=data, num_filter=24,  kernel=(5, 5), stride=(2,2))
    body = mx.sym.Activation(data=body, act_type='relu', name='relu1')
    body = mx.symbol.Pooling(data=body, kernel=(2, 2), stride=(2,2), pool_type='max')

    body = mx.sym.Convolution(data=body, num_filter=32,  kernel=(5, 5), stride=(2,2))
    body = mx.sym.Activation(data=body, act_type='relu', name='relu2')
    body = mx.symbol.Pooling(data=body, kernel=(2, 2), stride=(2,2), pool_type='max')

    body = mx.sym.Convolution(data=body, num_filter=64,  kernel=(5, 5))
    body = mx.sym.Activation(data=body, act_type='relu', name='relu3')
    #body = mx.symbol.Pooling(data=body, kernel=(2, 2), stride=(2,2), pool_type='max')
    
    flatten = mx.symbol.Flatten(data=body)

    body = mx.symbol.FullyConnected(data=flatten, name='fc0', num_hidden=100)
    body = mx.sym.Activation(data=body, act_type='relu', name='relu6')
    body = mx.sym.Dropout(data=body, p=0.1)

    body = mx.symbol.FullyConnected(data=body, name='fc1', num_hidden=50)
    body = mx.sym.Activation(data=body, act_type='relu', name='relu7')

    # NOTE: Add FC and Loss layers for each additional sensor/output you wish to get predictions for
    
    # For angle
    out = mx.symbol.FullyConnected(data=body, name='fc_angle', num_hidden=1)
    angle_out = mx.symbol.LinearRegressionOutput(data=out, label=target, name="angle")

    # For throttle
    t_out = mx.symbol.FullyConnected(data=body, name='fc_throttle', num_hidden=1)
    throttle_out = mx.symbol.LinearRegressionOutput(data=t_out, label=target2, name="throttle")

    sym_out = mx.symbol.Group([angle_out, throttle_out])
    sym_mod = mx.mod.Module(symbol=sym_out, label_names=(['angle', 'throttle']), context=ctx)
    
    shape = {"data" : (1, 3, 120, 160)}
    mx.viz.plot_network(symbol=sym_out, shape=shape)

    return sym_mod



from sklearn.metrics import mean_absolute_error
class MAECustom(mx.metric.EvalMetric):
    def __init__(self):
        super(MAECustom, self).__init__('maecustom')
        self.num_batch = 0
        # NOTE: Modify the lists below as you keep adding more sensors
        self.label_names = ['angle', 'throttle'] 
        self.output_names = ['angle_output', 'throttle_output']
        self.output_weights = [0.9, 0.1]
         
    def update_dict(self, labels, preds):
        for l, p in zip(self.label_names, self.output_names):
            #print "--", l, labels[l].shape, preds[p].shape
            for label, pred in zip(labels[l], preds[p]):
                label = label.asnumpy()
                pred = pred.asnumpy().flatten()
                #print self.label_names.index(l), l, mean_absolute_error(label, pred)
                w_sum = (self.output_weights[self.label_names.index(l)] * mean_absolute_error(label, pred))
                self.sum_metric += w_sum
                self.num_batch += 1
        self.num_inst += 1
        


class EvalCallback(object):
    '''
    Attempt at a Earlystopping solution
    
    1. epoch_end_callback: doesn't provide the metrics to the registered callback function, hence we can't use it to track
    metrics and save
    
    2. eval_end_callback: while it provides us with eval metrics, there isn't a clean way to stop the training, so the best
    thing to do is track and save the best model we have seen so far based on the metric and operator defined
    
    '''
    def __init__(self, model_prefix, op="max", save_model=True, patience=1, delta=0):
        self.model_prefix = model_prefix
        self.eval_metrics = []
        self.save_model = save_model
        self.metric_op = np.less if op == "min" else np.greater
        self.best_metric = np.Inf if self.metric_op == np.less else -np.Inf
        self.delta = delta #min difference between metric changes

    def get_loss_metrics(self):
        return self.eval_metrics
    
    def __call__(self, param):
        cur_epoch = param.epoch
        module_obj = param.locals['self']
        name_value = param.eval_metric.get_name_value()
        
        #NOTE: assuming 1 metric only
        name, cur_value = name_value[0]
        self.eval_metrics.append(cur_value)
        #print cur_value, self.best_metric, self.metric_op(cur_value - self.delta, self.best_metric)
        if self.metric_op(cur_value - self.delta, self.best_metric):
            self.best_metric = cur_value
            print('The best model found so far at epoch %05d with %s %s' % (cur_epoch, name, cur_value))
            if self.save_model:
                logging.info('Saving the Model')    
                module_obj.save_checkpoint(self.model_prefix, cur_epoch)
                param_fname = '%s-%04d.params' % (self.model_prefix, cur_epoch)
                os.rename(param_fname, '%s-best.params' % self.model_prefix ) #rename the model
        

