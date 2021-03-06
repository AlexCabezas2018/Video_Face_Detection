# Código adaptado de la siguiente fuente: https://tensorflow-object-detection-api-tutorial.readthedocs.io/en/latest/camera.html

import numpy as np
import os
import tensorflow as tf
import config
from matplotlib import pyplot as plt
from PIL import Image
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util
from object_detection.utils import ops as utils_ops

# Se comprueba que las rutas existan
modelOK = os.path.exists(config.MODEL_PATH)
imagesOK = os.path.exists(config.PATH_TO_IMAGES)
outputOK = os.path.exists(config.PATH_TO_OUTPUT_IMAGES)


def loadTensorFlowModel():
    """
    Carga el modelo de TensorFlow en memoria. Este modelo se escoge en el fichero de configuración "config.py"

    @return: detection_graph (Objeto simbolizando el grafo de detección a usar en cada fotograma),
            category_index (Indice perteneciente a la etiqueta que se va a mostrar en la detección)
    """
    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(config.PATH_TO_CKPT, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')

    label_map = label_map_util.load_labelmap(config.PATH_TO_LABELS)
    categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=config.NUM_CLASSES,
                                                                use_display_name=True)
    category_index = label_map_util.create_category_index(categories)

    return detection_graph, category_index


def run_detection_for_single_image(image, graph):
    """
    Esta funcion se encarga de realizar la detección para una imagen en especifico. Utiliza todas las funciones necesarias
    de tensorflow para poder llevar a cabo esta detección.

    @param image: Imagen sobre la que se debe hacer la detección facial
    @param graph: Objeto simbolizando el grafo de detección a usar en cada fotograma

    @return: output_dict (Diccionario con las caras encontradas en la imagen)

    """
    with graph.as_default():
        with tf.Session() as sess:
            ops = tf.get_default_graph().get_operations()
            all_tensor_names = {output.name for op in ops for output in op.outputs}
            tensor_dict = {}
            for key in [
                'num_detections', 'detection_boxes', 'detection_scores',
                'detection_classes', 'detection_masks'
            ]:
                tensor_name = key + ':0'
                if tensor_name in all_tensor_names:
                    tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
                        tensor_name)
            if 'detection_masks' in tensor_dict:
                detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
                detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])

                real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
                detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
                detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
                detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
                    detection_masks, detection_boxes, image.shape[0], image.shape[1])
                detection_masks_reframed = tf.cast(
                    tf.greater(detection_masks_reframed, 0.5), tf.uint8)

                tensor_dict['detection_masks'] = tf.expand_dims(
                    detection_masks_reframed, 0)
            image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

            # Realiza la inferencia
            output_dict = sess.run(tensor_dict,
                                   feed_dict={image_tensor: np.expand_dims(image, 0)})

            output_dict['num_detections'] = int(output_dict['num_detections'][0])
            output_dict['detection_classes'] = output_dict[
                'detection_classes'][0].astype(np.uint8)
            output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
            output_dict['detection_scores'] = output_dict['detection_scores'][0]
            if 'detection_masks' in output_dict:
                output_dict['detection_masks'] = output_dict['detection_masks'][0]
    return output_dict


def performDetection(detection_graph, category_index, image_path, i):
    """
    Esta funcion se encarga de realizar la detección. Prepara la imagen, infiere sobre ella y posteriormente la guarda
    en el directorio de salida que tenga especificado el usuario en el archivo 'config.py'

    @param detection_graph: Objeto simbolizando el grafo de detección a usar en cada fotograma
    @param category_index: Indice perteneciente a la etiqueta que se va a mostrar en la detección
    @param image_path: Ruta de la imagen a usar
    @param i: Número de imagen procesada
    """
    # Preparamos la imagen
    image = Image.open(image_path)
    image_np = np.array(image)
    image_np_expanded = np.expand_dims(image_np, axis=0)

    # Realizamos la detección
    output_dict = run_detection_for_single_image(image_np, detection_graph)

    # Se dibuja el marco en el fotograma
    vis_util.visualize_boxes_and_labels_on_image_array(
        image_np,
        output_dict['detection_boxes'],
        output_dict['detection_classes'],
        output_dict['detection_scores'],
        category_index,
        instance_masks=output_dict.get('detection_masks'),
        use_normalized_coordinates=True,
        line_thickness=4, )

    # Se guarda la imagen en su respectivo directorio
    plt.figure(figsize=config.IMAGE_SIZE)
    plt.imsave(config.PATH_TO_OUTPUT_IMAGES + str(i) + '.jpg', image_np)


if __name__ == "__main__":

    if modelOK and imagesOK:
        if not os.path.exists(config.PATH_TO_OUTPUT_IMAGES):
            os.makedirs(config.PATH_TO_OUTPUT_IMAGES)

        # Se obtiene el grafo de detección
        detection_graph, category_index = loadTensorFlowModel()

        # Se comienza a iterar sobre cada una de las imagenes
        i = 0
        for image_path in config.IMAGES_PATH:
            i += 1
            print("Procesando imagen {}".format(i))
            performDetection(detection_graph, category_index, image_path, i)
    else:
        print("Ha habido un error. Comprueba el fichero 'config.py'")
