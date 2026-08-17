"""
Regression tests for tensorflow-metal training correctness.

tensorflow-metal 1.2.0 paired with TensorFlow 2.19 / Keras 3 produces
incorrect results in compiled training on the Metal GPU. Eager training
matches CPU for the optimizers covered here, but compiled tf.function
execution is currently unsafe on the training path we care about.
KerasInterpreter therefore forces run_eagerly=True on Metal.

Tests are skipped on non-macOS platforms or when tensorflow-metal is absent.
"""
import numpy as np
import pytest

from donkeycar.parts.interpreter import _is_metal_installed

skip_no_metal = pytest.mark.skipif(
    not _is_metal_installed(),
    reason='tensorflow-metal not installed or not on macOS',
)


def _make_tiny_model(tf, seed=42):
    tf.random.set_seed(seed)
    ki0 = tf.keras.initializers.GlorotUniform(seed=seed)
    ki1 = tf.keras.initializers.GlorotUniform(seed=seed + 1)
    return tf.keras.Sequential([
        tf.keras.layers.Dense(4, activation='relu', input_shape=(3,),
                              kernel_initializer=ki0,
                              bias_initializer='zeros'),
        tf.keras.layers.Dense(1, kernel_initializer=ki1,
                              bias_initializer='zeros'),
    ])


def _fixed_data():
    np.random.seed(42)
    x = np.random.randn(8, 3).astype(np.float32)
    y = np.random.randn(8, 1).astype(np.float32)
    return x, y


def _optimizer(tf, name):
    if name == 'adam':
        return tf.keras.optimizers.Adam(1e-3)
    if name == 'sgd':
        return tf.keras.optimizers.SGD(1e-3)
    if name == 'rmsprop':
        return tf.keras.optimizers.RMSprop(1e-3)
    raise ValueError(f'unsupported optimizer: {name}')


def _cpu_reference_weights(tf, optimizer_name='adam'):
    """Return weights after one CPU training step."""
    x, y = _fixed_data()
    model = _make_tiny_model(tf)
    with tf.device('/CPU:0'):
        model.compile(optimizer=_optimizer(tf, optimizer_name), loss='mse')
        model.fit(x, y, epochs=1, batch_size=8, verbose=0)
    return [w.numpy().copy() for w in model.weights]


def _compiled_gradients(tf, model, x_t, y_t):
    @tf.function
    def grad_fn():
        with tf.GradientTape() as tape:
            pred = model(x_t, training=True)
            loss = tf.reduce_mean(tf.square(pred - y_t))
        return tape.gradient(loss, model.trainable_variables)

    return grad_fn()


@skip_no_metal
@pytest.mark.parametrize('optimizer_name', ['adam', 'sgd', 'rmsprop'])
def test_metal_training_matches_cpu_reference(optimizer_name):
    """Step 1: eager Metal training matches CPU for common optimizers."""
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        pytest.skip('Metal GPU not visible to TensorFlow')

    x, y = _fixed_data()
    cpu_weights = _cpu_reference_weights(tf, optimizer_name)

    model = _make_tiny_model(tf)
    model.compile(
        optimizer=_optimizer(tf, optimizer_name),
        loss='mse',
        run_eagerly=True,
    )
    model.fit(x, y, epochs=1, batch_size=8, verbose=0)
    metal_weights = [w.numpy().copy() for w in model.weights]

    for i, (cpu_w, metal_w) in enumerate(zip(cpu_weights, metal_weights)):
        np.testing.assert_allclose(
            metal_w,
            cpu_w,
            atol=1e-5,
            rtol=1e-4,
            err_msg=(
                f'weight[{i}]: Metal eager {optimizer_name} '
                f'diverges from CPU ref'
            ),
        )


@skip_no_metal
def test_step2a_gpu_gradients_match_cpu():
    """Step 2a: Eager gradient computation on Metal matches CPU."""
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        pytest.skip('Metal GPU not visible to TensorFlow')

    x, y = _fixed_data()
    x_t = tf.constant(x)
    y_t = tf.constant(y)

    model_cpu = _make_tiny_model(tf)
    _ = model_cpu(x_t)
    model_gpu = _make_tiny_model(tf)
    _ = model_gpu(x_t)
    for wc, wg in zip(model_cpu.weights, model_gpu.weights):
        wg.assign(wc)

    with tf.device('/CPU:0'):
        with tf.GradientTape() as tape_cpu:
            pred_cpu = model_cpu(x_t, training=True)
            loss_cpu = tf.reduce_mean(tf.square(pred_cpu - y_t))
        grads_cpu = tape_cpu.gradient(loss_cpu, model_cpu.trainable_variables)

    with tf.GradientTape() as tape_gpu:
        pred_gpu = model_gpu(x_t, training=True)
        loss_gpu = tf.reduce_mean(tf.square(pred_gpu - y_t))
    grads_gpu = tape_gpu.gradient(loss_gpu, model_gpu.trainable_variables)

    for i, (gc, gg) in enumerate(zip(grads_cpu, grads_gpu)):
        np.testing.assert_allclose(
            gg.numpy(), gc.numpy(), atol=1e-5, rtol=1e-4,
            err_msg=f'grad[{i}]: GPU gradient differs from CPU reference')


@skip_no_metal
def test_step2a_compiled_gpu_gradients_diverge_from_cpu():
    """Compiled tf.function gradients on Metal are currently unsafe."""
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        pytest.skip('Metal GPU not visible to TensorFlow')

    x, y = _fixed_data()
    x_t = tf.constant(x)
    y_t = tf.constant(y)

    model_cpu = _make_tiny_model(tf)
    _ = model_cpu(x_t)
    model_gpu = _make_tiny_model(tf)
    _ = model_gpu(x_t)
    for wc, wg in zip(model_cpu.weights, model_gpu.weights):
        wg.assign(wc)

    with tf.device('/CPU:0'):
        with tf.GradientTape() as tape_cpu:
            pred_cpu = model_cpu(x_t, training=True)
            loss_cpu = tf.reduce_mean(tf.square(pred_cpu - y_t))
        grads_cpu = tape_cpu.gradient(loss_cpu, model_cpu.trainable_variables)

    grads_gpu = _compiled_gradients(tf, model_gpu, x_t, y_t)
    max_diffs = [
        np.max(np.abs(gc.numpy() - gg.numpy()))
        for gc, gg in zip(grads_cpu, grads_gpu)
    ]

    assert max(max_diffs) > 1e-3, (
        'Compiled Metal gradients unexpectedly match CPU; re-evaluate the '
        'Metal workaround before changing production code.')


@skip_no_metal
def test_step2b_eager_apply_on_gpu_matches_cpu():
    """Step 2b: eager apply_gradients on GPU matches CPU reference."""
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        pytest.skip('Metal GPU not visible to TensorFlow')

    x, y = _fixed_data()
    x_t = tf.constant(x)
    y_t = tf.constant(y)

    cpu_weights = _cpu_reference_weights(tf)

    model = _make_tiny_model(tf)
    _ = model(x_t)
    model_ref = _make_tiny_model(tf)
    _ = model_ref(x_t)
    for wr, wm in zip(model_ref.weights, model.weights):
        wm.assign(wr)

    optimizer = tf.keras.optimizers.Adam(1e-3)
    with tf.GradientTape() as tape:
        pred = model(x_t, training=True)
        loss = tf.reduce_mean(tf.square(pred - y_t))
    grads = tape.gradient(loss, model.trainable_variables)
    # Eager apply (not inside tf.function) - correct on Metal GPU
    optimizer.apply_gradients(zip(grads, model.trainable_variables))

    for i, (cpu_w, model_w) in enumerate(zip(cpu_weights, model.weights)):
        np.testing.assert_allclose(
            model_w.numpy(), cpu_w, atol=1e-5, rtol=1e-4,
            err_msg=f'weight[{i}]: eager GPU apply diverges from CPU ref')


@skip_no_metal
@pytest.mark.parametrize('optimizer_name', ['adam', 'sgd', 'rmsprop'])
def test_keras_interpreter_compile_sets_run_eagerly(optimizer_name):
    """Production path: KerasInterpreter uses eager training on Metal."""
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        pytest.skip('Metal GPU not visible to TensorFlow')

    x, y = _fixed_data()
    cpu_weights = _cpu_reference_weights(tf, optimizer_name)

    from donkeycar.parts.interpreter import KerasInterpreter

    interp = KerasInterpreter()
    model = _make_tiny_model(tf)
    interp.model = model
    interp.input_keys = []
    interp.output_keys = []
    interp.shapes = ({}, {})
    interp.compile(optimizer=_optimizer(tf, optimizer_name), loss='mse')

    assert model.run_eagerly, (
        'KerasInterpreter.compile() must set run_eagerly=True on Metal')

    dataset = tf.data.Dataset.from_tensor_slices((x, y)).batch(8)
    interp.fit(x=dataset, steps_per_epoch=1, batch_size=8,
               callbacks=[], validation_data=None,
               validation_steps=0, epochs=1, verbose=0)

    for i, (cpu_w, model_w) in enumerate(zip(cpu_weights, model.weights)):
        np.testing.assert_allclose(
            model_w.numpy(),
            cpu_w,
            atol=1e-5,
            rtol=1e-4,
            err_msg=(
                f'weight[{i}]: Metal eager {optimizer_name} fit incorrect'
            ),
        )


@skip_no_metal
@pytest.mark.parametrize('optimizer_name', ['adam', 'sgd', 'rmsprop'])
def test_compiled_metal_training_diverges_for_common_optimizers(
    optimizer_name,
):
    """Compiled Metal training is unsafe across common optimizers."""
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        pytest.skip('Metal GPU not visible to TensorFlow')

    x, y = _fixed_data()
    cpu_weights = _cpu_reference_weights(tf, optimizer_name)

    model = _make_tiny_model(tf)
    model.compile(optimizer=_optimizer(tf, optimizer_name), loss='mse')
    model.fit(x, y, epochs=1, batch_size=8, verbose=0)
    metal_weights = [w.numpy().copy() for w in model.weights]
    max_diffs = [
        np.max(np.abs(cpu_w - metal_w))
        for cpu_w, metal_w in zip(cpu_weights, metal_weights)
    ]

    assert max(max_diffs) > 1e-4, (
        f'Compiled Metal {optimizer_name} unexpectedly matches CPU; '
        're-evaluate the eager-only Metal workaround before changing '
        'production code.'
    )


@skip_no_metal
def test_keras_interpreter_accepts_dict_inputs():
    """KerasInterpreter must support dict-shaped inputs used by train."""
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        pytest.skip('Metal GPU not visible to TensorFlow')

    from donkeycar.parts.interpreter import KerasInterpreter

    x, y = _fixed_data()
    inputs = tf.keras.Input(shape=(3,), name='img_in')
    hidden = tf.keras.layers.Dense(4, activation='relu')(inputs)
    outputs = tf.keras.layers.Dense(1, name='angle_out')(hidden)
    model = tf.keras.Model(inputs=inputs, outputs=outputs)

    interp = KerasInterpreter()
    interp.model = model
    interp.input_keys = ['img_in']
    interp.output_keys = ['angle_out']
    interp.shapes = ({'img_in': (None, 3)}, {'angle_out': (None, 1)})
    interp.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss='mse')

    dataset = tf.data.Dataset.from_tensor_slices(({'img_in': x}, y)).batch(8)
    history = interp.fit(
        x=dataset,
        steps_per_epoch=1,
        batch_size=8,
        callbacks=[],
        validation_data=None,
        validation_steps=0,
        epochs=1,
        verbose=0,
    )

    assert history.history['loss'], 'expected one successful training step'
