import argparse
import os
import shutil
import time

import pdb
import torch.nn.parallel
import torch.optim
import torch.utils.data
from PIL import Image
import scipy.io as sio
from sklearn.svm import SVR
from sklearn import preprocessing
from sklearn.model_selection import train_test_split
from sklearn.model_selection import GridSearchCV
from sklearn.externals import joblib
from comm_model import *
import skvideo.io
import argparse
import warnings

svr_save_path = './trained_models/svr_mode.pkl'
svr_process_path = './trained_models/svr_process.pkl'
feature_mode_path = './trained_models/model_best.pth.tar'
image_dir = './ChallengeDB_release/Images'
matfn = './ChallengeDB_release/Data/AllMOS_release.mat'
mat_img_name = './ChallengeDB_release/Data/AllImages_release.mat'


warnings.filterwarnings("ignore")
parser = argparse.ArgumentParser()
parser.add_argument("--vdir", help="video dir")
args = parser.parse_args()
vdir = args.vdir


def load_feature(feature_model, video_path):
    normalize = get_imagenet_normalize()
    img_transform = transforms.Compose([transforms.ToTensor(), normalize])

    X = np.array([])
    crop_w = 224
    crop_h = 224
    img_w = 0
    img_h = 0
    crop_num_w = 5
    crop_num_h = 5

    frames = skvideo.io.vreader(video_path)
    for frame in frames:
        if frame is None:
            break
        crop_imgs = np.array([])
        crop_out = None
        img = frame
        img_w, img_h = img.shape[1], img.shape[0]
        crop_box = get_crop_box(
            img_w, img_h, crop_w, crop_h, crop_num_w, crop_num_h)
        for box in crop_box:
            w, h, w2, h2 = box
            w = int(w)
            h = int(h)
            w2 = int(w2)
            h2 = int(h2)
            part = img[h:h2, w:w2]
            crop_imgs = np.append(
                crop_imgs, img_transform(part))
        crop_imgs = crop_imgs.reshape(crop_num_w * crop_num_h, 3, 224, 224)
        crop_imgs = torch.from_numpy(crop_imgs).float()
        crop_out = feature_model.extract_feature(crop_imgs)
        crop_out = np.average(crop_out, axis=0)

        X = np.append(X, crop_out)
    X = X.reshape(-1, 4096)

    return X


feature_model = FeatureMode(feature_mode_path)
data_x = load_feature(feature_model, vdir)

scaler_x = preprocessing.StandardScaler().fit(data_x)
joblib.dump(scaler_x, svr_process_path)
X_test = scaler_x.transform(data_x)

clf = joblib.load(svr_save_path)
pred_y_test = clf.predict(X_test)
print('test score:', np.mean(pred_y_test))
