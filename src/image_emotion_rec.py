import cv2
import dlib
import numpy as np
from keras.models import load_model
from mxnet.gluon import nn
from utils.builddata import preprocess_input
from collections import namedtuple
import mxnet as mx
from mxnet import nd
from time import time
import os
cur_path = os.path.dirname(__file__)
parent_path = os.path.dirname(cur_path)
detect_model_path = parent_path + '/trained_models\detection_models\haarcascade_frontalface_default.xml'
emotion_model_path = parent_path +'/trained_models/emotion_models/fer2013_mini_XCEPTION.102-0.66.hdf5'
emotion_labels_ck={0: 'neutral', 1: 'anger', 2: 'contempt', 3: 'disgust',
             4: 'fear', 5:'happy', 6:'sadness', 7:'surprise'}

emotion_labels_fer={0:'angry',1:'disgust',2:'fear',3:'happy',
                4:'sad',5:'surprise',6:'neutral'}
emotion_classifier = load_model(emotion_model_path)

class EmotionModel(object):
    """
    select the emotion classfier model had been trained
    """
    def __init__(self,data_name = 'fer2013',image=None):
        self.data_name = data_name
        self._image =image
    def model_predict(self):
        if self.data_name == 'ck':
            symnet = mx.symbol.load('./model/vgg/ck-vgg11-symbol.json')
            # print(symnet)
            mod = mx.mod.Module(symbol=symnet, context=mx.cpu())
            mod.bind(data_shapes=[('data', (1, 3, 224, 224))], for_training=False)
            mod.load_params('./model/vgg/ck-vgg11-0050.params')
            batch = namedtuple('batch', ['data'])
            target_img = nd.array(np.reshape(self._image, (-1, 3, 224, 224)))
            target_img = target_img/255
            mod.forward(data_batch=batch([target_img]), is_train=False)
            out = mod.get_outputs()
            prob = out[0]
            predicted_labels = prob.argmax(axis=1)
            idx = int(predicted_labels.asscalar())
            return emotion_labels_ck[idx]
        elif self.data_name=='fer2013':
            gray_face = preprocess_input(self._image, True)
            gray_face = np.expand_dims(gray_face, 0)
            gray_face = np.expand_dims(gray_face, -1)
            emotion_prediction = emotion_classifier.predict(gray_face)
            emotion_probability = np.max(emotion_prediction)
            emotion_label_arg = np.argmax(emotion_prediction)
            emotion_text = emotion_labels_fer[emotion_label_arg]
            return emotion_text

# parameters for loading data and images
def detect_faces(image=None,face_size =(224,224),offset = 20,method = 'dlib'):

    faces = []
    if method =='cv':
        detector = cv2.CascadeClassifier(detect_model_path)
        dets = detector.detectMultiScale(image,scaleFactor=1.1,minNeighbors= 5,minSize=(48,48))
        for face_coordinates in dets:
            x, y, w, h = face_coordinates
            x1,x2, y1, y2 = x - offset, x + w + offset, y - offset, y + h + offset
            face = image[y1:y2, x1: x2]
            try:
                faces.append(cv2.resize(face,face_size))
            except:
                continue
        return faces, dets
    elif method =='dlib':
        detector = dlib.get_frontal_face_detector()
        dets, _ = detector(image, 1), []
        rect = []
        for _, d in enumerate(dets):
                left, right, top, bottom = d.left() - offset, d.right() + offset, d.top() - offset, d.bottom() + offset
                face = image[top:bottom, left:right]
                try:
                    faces.append(cv2.resize(face,face_size))
                    rect.append((d.left(),d.top(),d.right() - d.left(),d.bottom() - d.top()))
                except:
                    continue
        return faces, rect
def draw_bounding_box(face_coordinates, image_array, color):
    x, y, w, h = face_coordinates
    cv2.rectangle(image_array, (x, y), (x + w, y + h), color, 2)

def draw_text(coordinates, image_array, text, color, x_offset=0, y_offset=0,
                                                font_scale=2, thickness=2):
    x, y = coordinates[:2]
    cv2.putText(image_array, text, (x + x_offset, y + y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, color, thickness, cv2.LINE_AA)
color = (0, 255, 0)

# starting video streaming
cv2.namedWindow('window_frame')
image_dir = '../test_image\Lecun&hiton.png'
flag_video = False
flag_img = False
if flag_video:
    emotion_video = '../test_image/emotion.avi'
    img_root = '../test_image/'
    fps = 15
    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(img_root+'result_emotion.avi',fourcc, fps, (640,490))

    cap = cv2.VideoCapture(emotion_video)
    from PIL import Image
    import imageio
    frame = []
    while(cap.isOpened()):
        ret, bgr_image = cap.read()

        gray_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
        gray_image = cv2.resize(gray_image, dsize=(0, 0), fx=0.25, fy=0.25)
        # rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        start = time()
        face_size = emotion_classifier.input_shape[1:3]
        faces, bboxs = detect_faces(gray_image, face_size=face_size, method='cv')
        print('detect face cost time: %f' % (time() - start))
        for face, bbox in zip(faces, bboxs):
            try:
                start = time()
                emotion = EmotionModel(data_name='fer2013', image=face).model_predict()
                print('predict emotion cost time: %f' % (time() - start))
            except:
                continue

            bbox = [x * 4 for x in bbox]
            draw_bounding_box(bbox, bgr_image, color)
            draw_text(bbox, bgr_image, emotion, color, x_offset=0, y_offset=0, font_scale=2, thickness=2)
        try:
            out.write(bgr_image)
            cv2.imshow('window_frame', bgr_image)
        except:
            continue
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
elif flag_img:
    bgr_image = cv2.imread(image_dir)
    gray_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    # gray_image = cv2.resize(gray_image,dsize=(0,0),fx=0.25,fy=0.25)
    start = time()
    face_size = emotion_classifier.input_shape[1:3]
    faces, bboxs= detect_faces(gray_image,face_size=face_size,method='dlib')
    print('detect face cost time: %f'%(time()-start))
    for face, bbox in zip(faces,bboxs):
        try:
            start = time()
            emotion = EmotionModel(data_name='fer2013',image=face).model_predict()
            print('predict emotion cost time: %f'%(time()-start))
        except:
            continue
        # bbox = [x*4 for x in bbox]
        draw_bounding_box(bbox, bgr_image, color)
        draw_text(bbox, bgr_image, emotion, color, x_offset=0, y_offset=0,font_scale=1, thickness=1)
    cv2.imwrite('../test_image/image_result.png',bgr_image)
    cv2.imshow('window_frame', bgr_image)
    if cv2.waitKey() & 0xFF == ord('q'):
        cv2.destroyAllWindows()
else:
    from PIL import Image
    emotion_video = '../test_image/emotion.avi'
    img_root = '../test_image/'
    img_dir = '../S052'
    img_root = '../test_image/'
    frame = []
    for file in os.listdir(img_dir):
        dir_path = os.path.join(img_dir, file)
        for img in os.listdir(dir_path):
            img_file = dir_path + '/' + img
            bgr_image = cv2.imread(img_file)
            gray_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
            gray_image = cv2.resize(gray_image, dsize=(0, 0), fx=0.25, fy=0.25)
            # rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
            start = time()
            face_size = emotion_classifier.input_shape[1:3]
            faces, bboxs = detect_faces(gray_image, face_size=face_size, method='cv')
            print('detect face cost time: %f' % (time() - start))
            for face, bbox in zip(faces, bboxs):
                try:
                    start = time()
                    emotion = EmotionModel(data_name='fer2013', image=face).model_predict()
                    print('predict emotion cost time: %f' % (time() - start))
                except:
                    continue

                bbox = [x * 4 for x in bbox]
                draw_bounding_box(bbox, bgr_image, color)
                draw_text(bbox, bgr_image, emotion, color, x_offset=0, y_offset=0, font_scale=2, thickness=2)
            try:
                img = Image.fromarray(bgr_image)
                frame.append(img)
                cv2.imshow('window_frame', bgr_image)
            except:
                continue
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    cv2.destroyAllWindows()
    img.save(img_root+'emotion.gif',save_all=True, append_images=frame,loop=1,duration=1,comment=b"aaabb")


