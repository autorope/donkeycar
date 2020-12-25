def get_model_by_type(model_type, cfg, checkpoint_path=None):
    '''
    given the string model_type and the configuration settings in cfg
    create a Torch model and return it.
    '''
    from donkeycar.parts.pytorch.ResNet18 import ResNet18

    if model_type is None:
        model_type = cfg.DEFAULT_MODEL_TYPE
    print("\"get_model_by_type\" model Type is: {}".format(model_type))

    input_shape = (cfg.BATCH_SIZE, cfg.IMAGE_DEPTH, cfg.IMAGE_H, cfg.IMAGE_W)

    if model_type == "linear":
        model = ResNet18(input_shape=input_shape)
    else:
        raise Exception("Unknown model type {:}, supported types are "
                        "linear"
                        .format(model_type))

    if checkpoint_path:
        print("Loading model from checkpoint {}".format(checkpoint_path))
        model.load_from_checkpoint(checkpoint_path)

    return model
