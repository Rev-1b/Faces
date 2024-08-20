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


class FaceExtractor(SaveMixin):
    def __init__(self, video_path, video_name, output_dir, deepfake, frame_skip=10):
        self.video_name = video_name
        self.frame_skip = frame_skip
        self.video_path = video_path
        self.output_dir = output_dir
        self.is_deepfake = deepfake
        self.faces_df = pd.DataFrame(columns=["filepath", "deepfake"])

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

    @staticmethod
    def extract_faces_from_frame(frame):
        rgb_frame = frame[:, :, ::-1]
        return face_recognition.face_locations(rgb_frame)

    def adjust_face_size(self, frame, face_location):
        top, right, bottom, left = face_location
        height, width = bottom - top, right - left

        # Увеличиваем размер на 20%
        top = max(0, top - height // 10)
        bottom = min(frame.shape[0], bottom + height // 10)
        left = max(0, left - width // 10)
        right = min(frame.shape[1], right + width // 10)

        return frame[top:bottom, left:right]

    def record_face_data(self, face_path):
        self.faces_df = pd.concat(
            [self.faces_df, pd.DataFrame({"filepath": [face_path], "deepfake": [self.is_deepfake]})]
        )

    def save_face_data(self, temp_csv_path):
        self.faces_df.to_csv(temp_csv_path, index=False)
        print("Обработка видео завершена.")