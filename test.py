import tensorflow as tf
model = tf.keras.models.load_model("models/best_finetuned_model.h5")
print(model.input_shape, model.output_shape)