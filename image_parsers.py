import os
import uuid

import cv2
import face_recognition
import pandas as pd


class SaveMixin:
    def save(self, face_image, video_name: str, output_dir):
        face_filename = f"{video_name.rstrip('.mp4')}_{uuid.uuid4()}.jpg"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        cv2.imwrite(os.path.join(output_dir, face_filename), face_image)
        return face_filename


class BaseExtractor:
    def __init__(self, video_path, video_name, output_dir, deepfake, frame_skip=5):
        self.video_name = video_name
        self.frame_skip = frame_skip
        self.video_path = video_path
        self.output_dir = output_dir
        self.is_deepfake = deepfake
        self.faces_df = pd.DataFrame(columns=["filepath", "deepfake"])

    @staticmethod
    def extract_faces_from_frame(frame):
        rgb_frame = frame[:, :, ::-1]
        return face_recognition.face_locations(rgb_frame)

    @staticmethod
    def adjust_face_size(frame, face_location):
        top, right, bottom, left = face_location
        height, width = bottom - top, right - left

        # Увеличиваем размер на 20%

        top = max(0, top - height // 3)
        bottom = min(frame.shape[0], bottom + height // 3)
        left = max(0, left - width // 3)
        right = min(frame.shape[1], right + width // 3)

        return frame[top:bottom, left:right]

    def record_face_data(self, face_path):
        self.faces_df = pd.concat(
            [self.faces_df, pd.DataFrame({"filepath": [face_path], "deepfake": [self.is_deepfake]})]
        )

    def save_face_data(self, temp_csv_path):
        self.faces_df.to_csv(temp_csv_path, index=False)
        print("Обработка видео завершена.")


class FaceRecognitionExtractor(BaseExtractor, SaveMixin):
    def process_video(self):
        video_capture = cv2.VideoCapture(self.video_path)
        frame_count, total_faces = 0, 0

        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("Все кадры обработаны, завершаем.")
                break

            if frame_count % (self.frame_skip + 1) == 0:
                face_locations = self.extract_faces_from_frame(frame)
                for face_location in face_locations:
                    face_image = self.adjust_face_size(frame, face_location)
                    face_filename = self.save(face_image, self.video_name, self.output_dir)
                    self.record_face_data(face_filename)

                total_faces += len(face_locations)
                print(f"Обработано кадров: {frame_count}, Найдено лиц: {total_faces}")

            frame_count += 1

        video_capture.release()


class HaarcascadesExtractor(BaseExtractor, SaveMixin):
    def __init__(self, video_path, video_name, output_dir, deepfake):
        super().__init__(video_path, video_name, output_dir, deepfake)
        self.face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    def process_video(self):
        video_capture = cv2.VideoCapture(self.video_path)
        frame_count, total_faces = 0, 0

        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("Все кадры обработаны, завершаем.")
                break

            if frame_count % (self.frame_skip + 1) == 0:
                face_locations = self.extract_faces_from_frame(frame)
                for (x, y, w, h) in face_locations:

                    # if w < 200 or h < 200:
                    #     continue

                    # Увеличиваем размеры лица на 20%
                    new_w = int(w * 1.3)
                    new_h = int(h * 1.3)
                    new_x = max(x - int((new_w - w) / 2), 0)
                    new_y = max(y - int((new_h - h) / 2), 0)

                    face_image = frame[new_y:new_y + new_h, new_x:new_x + new_w]
                    face_filename = self.save(face_image, self.video_name, self.output_dir)
                    self.record_face_data(face_filename)

                total_faces += len(face_locations)
                print(f"Обработано кадров: {frame_count}, Найдено лиц: {total_faces}")

            frame_count += 1

        video_capture.release()

    def extract_faces_from_frame(self, frame):
        gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_classifier.detectMultiScale(
            gray_img,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        return faces  # возвращает список лиц в формате (x, y, w, h)


