import os
import uuid

import cv2
import pandas as pd
from PIL import Image
from facenet_pytorch import MTCNN
from time import sleep

from tqdm import tqdm


class SaveMixin:
    @staticmethod
    def save(face_image, video_name: str, output_dir):
        face_filename = f"{video_name.rstrip('.mp4')}_{uuid.uuid4()}.jpg"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        cv2.imwrite(os.path.join(output_dir, face_filename), face_image)
        return face_filename


class BaseExtractor(SaveMixin):
    def __init__(self, video_path: str, video_name: str, output_dir: str, deepfake: bool, crop_image: bool = False,
                 frame_skip: int = 10):
        self.crop_image = crop_image
        self.video_name = video_name
        self.frame_skip = frame_skip
        self.video_path = video_path
        self.output_dir = output_dir
        self.is_deepfake = deepfake
        self.faces_df = pd.DataFrame(columns=["filepath", "deepfake"])

    def process_video(self):
        video_capture = cv2.VideoCapture(self.video_path)
        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count, total_faces = 0, 0

        if self.crop_image:
            print('Изображение будет обрезано')

        with tqdm(total=total_frames, desc="Обработка кадров", unit="кадров") as pbar:
            while True:
                ret, frame = video_capture.read()
                if not ret:
                    print("Все кадры обработаны, завершаем.")
                    break

                if frame_count % self.frame_skip == 0:
                    if self.is_deepfake and self.crop_image:
                        frame = self.get_right_half(frame)

                    total_faces = self.on_frame(total_frames, frame_count, total_faces, frame)
                    pbar.set_postfix({'Найдено лиц': total_faces})

                frame_count += 1
                pbar.update(1)

        video_capture.release()

    def on_frame(self, total_frames, frame_count, total_faces, frame):
        raise NotImplementedError('Не переопределен метод on_frame')

    @staticmethod
    def get_right_half(frame):
        width = frame.shape[1]
        return frame[:, width // 2:]

    @staticmethod
    def adjust_face_size(frame, face_location):
        top, right, bottom, left = face_location
        height, width = bottom - top, right - left

        top = max(0, top - height // 3)
        bottom = min(frame.shape[0], bottom + height // 3)
        left = max(0, left - width // 3)
        right = min(frame.shape[1], right + width // 3)

        return frame[top:bottom, left:right]

    @staticmethod
    def validate_face(face):
        mtcnn = MTCNN()
        image = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
        boxes, _ = mtcnn.detect(image)
        return boxes

    def record_face_data(self, face_path):
        self.faces_df = pd.concat(
            [self.faces_df, pd.DataFrame({"filepath": [face_path], "deepfake": [self.is_deepfake]})]
        )

    def save_face_data(self, temp_csv_path):
        self.faces_df.to_csv(temp_csv_path, index=False)
        print("Обработка видео завершена.")


class HaarcascadesExtractor(BaseExtractor):
    def __init__(self, video_path: str, video_name: str, output_dir: str, deepfake: bool, crop_image: bool = False,
                 frame_skip: int = 7):
        super().__init__(video_path, video_name, output_dir, deepfake, crop_image, frame_skip)
        self.face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def on_frame(self, total_frames, frame_count, total_faces, frame):
        face_locations = self.extract_faces_from_frame(frame)
        for coords in face_locations:
            face_image = self.adjust_face_size(frame, coords)

            # Дополнительная проверка на минимальное разрешение картинки и наличие
            # на ней лица (Отсеивает почти весь мусор)
            if face_image is None or self.validate_face(face_image) is None:
                continue

            face_filename = self.save(face_image, self.video_name, self.output_dir)
            self.record_face_data(face_filename)

            total_faces += 1

        return total_faces

    def extract_faces_from_frame(self, frame):
        gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_classifier.detectMultiScale(
            gray_img,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)  # ПОПРАВИТЬ
        )
        return faces  # возвращает список лиц в формате (x, y, w, h)

    @staticmethod
    def adjust_face_size(frame, face_location):
        (x, y, w, h) = face_location

        new_w = int(w * 1.3)
        new_h = int(h * 1.3)
        new_x = max(x - int((new_w - w) / 2), 0)
        new_y = max(y - int((new_h - h) / 2), 0)

        return frame[new_y:new_y + new_h, new_x:new_x + new_w] if new_w >= 200 and new_h >= 200 else None