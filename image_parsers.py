import os
import uuid

import cv2
import face_recognition
import pandas as pd

import torch
import torchvision.transforms as transforms
from facenet_pytorch import MTCNN
from torchvision.models import resnet18, ResNet18_Weights
from PIL import Image


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
        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count, total_faces = 0, 0

        while True:
            ret, raw_frame = video_capture.read()
            if not ret:
                print("Все кадры обработаны, завершаем.")
                break

            frame = self.get_cropped_frame(raw_frame)
            if frame_count % (self.frame_skip + 1) == 0:
                face_locations = self.extract_faces_from_frame(frame)
                for face_location in face_locations:
                    face_image = self.adjust_face_size(raw_frame, face_location)
                    face_filename = self.save(face_image, self.video_name, self.output_dir)
                    self.record_face_data(face_filename)

                total_faces += len(face_locations)
                print(f"Обработано кадров: {frame_count}/{total_frames}, Найдено лиц: {total_faces}")

            frame_count += 1

        video_capture.release()

    @staticmethod
    def get_cropped_frame(frame):
        height, width = frame.shape[:2]
        center_x, center_y = width // 2, height // 2
        new_width, new_height = width // 2, height // 2
        left = max(center_x - new_width // 2, 0)
        top = max(center_y - new_height // 2, 0)
        right = min(center_x + new_width // 2, width)
        bottom = min(center_y + new_height // 2, height)

        return frame[top:bottom, left:right]


class HaarcascadesExtractor(BaseExtractor, SaveMixin):
    def __init__(self, video_path, video_name, output_dir, deepfake):
        super().__init__(video_path, video_name, output_dir, deepfake)
        self.face_classifier = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

        # Загружаем предобученную модель с правильным использованием параметра weights
        self.face_recognition_model = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        self.face_recognition_model.eval()

        # Задаем трансформации для подготовки изображений
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

    def process_video(self):
        video_capture = cv2.VideoCapture(self.video_path)
        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count, total_faces = 0, 0

        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("Все кадры обработаны, завершаем.")
                break

            if frame_count % (self.frame_skip + 1) == 0:
                face_locations = self.extract_faces_from_frame(frame)
                for (x, y, w, h) in face_locations:
                    new_w = int(w * 1.3)
                    new_h = int(h * 1.3)
                    new_x = max(x - int((new_w - w) / 2), 0)
                    new_y = max(y - int((new_h - h) / 2), 0)

                    face_image = frame[new_y:new_y + new_h, new_x:new_x + new_w]

                    # Преобразуем изображение для модели PyTorch
                    # pil_image = Image.fromarray(cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB))
                    # input_tensor = self.transform(pil_image).unsqueeze(0)
                    #
                    # # Используем модель для предсказания
                    # with torch.no_grad():
                    #     output = self.face_recognition_model(input_tensor)
                    #     _, predicted_class = output.max(1)
                    #
                    # # Если предсказанный класс не соответствует лицу, пропускаем
                    # if predicted_class.item() != 1:  # Предполагаем, что класс 1 соответствует лицу
                    #     continue

                    mtcnn = MTCNN()
                    image = Image.fromarray(cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB))
                    boxes, _ = mtcnn.detect(image)

                    if boxes is None:
                        continue

                    face_filename = self.save(face_image, self.video_name, self.output_dir)
                    self.record_face_data(face_filename)

                    total_faces += len(face_locations)
                print(f"Обработано кадров: {frame_count}/{total_frames}, Найдено лиц: {total_faces}")

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


class DeepFaceExtractor(BaseExtractor, SaveMixin):
    def __init__(self, video_path: str, video_name: str, output_dir: str, deepfake: bool, frame_skip: int = 5):
        super().__init__(video_path, video_name, output_dir, deepfake, frame_skip)
        self.mtcnn = MTCNN()

    def process_video(self):
        video_capture = cv2.VideoCapture(self.video_path)
        total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count, total_faces = 0, 0

        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("Все кадры обработаны, завершаем.")
                break

            if frame_count % (self.frame_skip + 1) == 0:
                face_images = self.extract_faces_from_frame(frame)
                for face_image in face_images:
                    face_filename = self.save(face_image, self.video_name, self.output_dir)
                    self.record_face_data(face_filename)

                total_faces += len(face_images)
                print(f"Обработано кадров: {frame_count}/{total_frames}, Найдено лиц: {total_faces}")

            frame_count += 1

        video_capture.release()

    def extract_faces_from_frame(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_frame)
        boxes, _ = self.mtcnn.detect(pil_image)

        face_images = []
        if boxes is not None:
            for box in boxes:
                x1, y1, x2, y2 = map(int, box)
                face_image = self.adjust_face_size(frame, (y1, x2, y2, x1))

                # face_image = frame[y1:y2, x1:x2]
                if face_image.size == 0:  # Skip empty face images
                    print('bruh')
                    continue
                face_images.append(face_image)
        return face_images

