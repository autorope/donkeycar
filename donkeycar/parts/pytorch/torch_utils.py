import os


def get_model_by_type(model_type, cfg, checkpoint_path=None):
    '''
    given the string model_type and the configuration settings in cfg
    create a Torch model and return it.
    '''
    if model_type is None:
        model_type = cfg.DEFAULT_MODEL_TYPE
    print("\"get_model_by_type\" model Type is: {}".format(model_type))

    input_shape = (cfg.BATCH_SIZE, cfg.IMAGE_DEPTH, cfg.IMAGE_H, cfg.IMAGE_W)

    if model_type == "resnet18":
        from donkeycar.parts.pytorch.ResNet18 import ResNet18
        # ResNet18 will always use the following input size
        # regardless of what the user specifies. This is necessary since
        # the model is pre-trained on ImageNet
        input_shape = (cfg.BATCH_SIZE, 3, 224, 224)
        model = ResNet18(input_shape=input_shape)
    else:
        raise Exception("Unknown model type {:}, supported types are "
                        "resnet18"
                        .format(model_type))

    if checkpoint_path:
        print("Loading model from checkpoint {}".format(checkpoint_path))
        model.load_from_checkpoint(checkpoint_path)

    return model
