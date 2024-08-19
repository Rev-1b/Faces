import os
import platform
import shutil
import tempfile
import uuid

import click
import cv2
import face_recognition
import pandas as pd
from pytubefix import YouTube


class VideoDownloader:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def download(self):
        raise NotImplementedError("Этот метод должен быть реализован в дочернем классе.")

    @staticmethod
    def show_progress(stream, chunk, bytes_remaining):
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        completion_percentage = bytes_downloaded / total_size * 100
        print(f"\rЗагрузка видео {bytes_downloaded}/{total_size} байт: {completion_percentage:.2f}%", end="",
              flush=True)


class YouTubeVideoDownloader(VideoDownloader):
    def __init__(self, output_dir, youtube_url, resolution='360p'):
        super().__init__(output_dir)
        self.youtube_url = youtube_url
        self.resolution = resolution

    def download(self):
        yt = YouTube(self.youtube_url, on_progress_callback=self.show_progress, use_oauth=True)
        video_stream = yt.streams.filter(adaptive=True, type="video", resolution=self.resolution,
                                         file_extension='mp4').first()

        if video_stream is None:
            print('Неподходящее разрешение, пробую другое')
            video_stream = yt.streams.filter(adaptive=True, type="video", resolution='360p',
                                             file_extension='mp4').first()

        if video_stream is None:
            raise ValueError("Не удалось найти видеопоток без звука на YouTube.")

        print(f"Выбран поток с разрешением: {video_stream.resolution}")
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        video_stream.download(output_path=os.path.dirname(temp_file.name), filename=os.path.basename(temp_file.name))
        print("\nЗагрузка завершена!")
        return temp_file.name


class LocalVideoDownloader(VideoDownloader):
    def __init__(self, output_dir, video_filename):
        super().__init__(output_dir)
        self.video_filename = video_filename

    def download(self):
        video_path = os.path.join(self.output_dir, self.video_filename)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видео {self.video_filename} не найдено в папке {self.output_dir}.")
        return video_path


class FaceExtractor:
    def __init__(self, video_file, output_dir, deepfake):
        self.video_file = video_file
        self.output_dir = output_dir
        self.is_deepfake = deepfake
        self.faces_df = pd.DataFrame(columns=["filename", "deepfake"])

    def process_video(self):
        video_capture = cv2.VideoCapture(self.video_file)
        frame_count, total_faces = 0, 0

        while True:
            ret, frame = video_capture.read()
            if not ret:
                print("Все кадры обработаны, завершаем.")
                break

            face_locations = self.extract_faces_from_frame(frame)
            for face_location in face_locations:
                face_filename = self.save_face(frame, face_location)
                self.record_face_data(face_filename)

            frame_count += 1
            total_faces += len(face_locations)
            print(f"Обработано кадров: {frame_count}, Найдено лиц: {total_faces}")

        video_capture.release()

    def extract_faces_from_frame(self, frame):
        rgb_frame = frame[:, :, ::-1]
        return face_recognition.face_locations(rgb_frame)

    def save_face(self, frame, face_location):
        top, right, bottom, left = face_location
        face_image = frame[top:bottom, left:right]
        face_filename = f"{uuid.uuid4()}.jpg"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        cv2.imwrite(os.path.join(self.output_dir, face_filename), face_image)
        return face_filename

    def record_face_data(self, face_filename):
        self.faces_df = pd.concat(
            [self.faces_df, pd.DataFrame({"filename": [face_filename], "deepfake": [self.is_deepfake]})]
        )

    def save_face_data(self, temp_csv_path):
        self.faces_df.to_csv(temp_csv_path, index=False)
        print("Обработка видео завершена.")


class FaceCleanupManager:
    def __init__(self, temp_csv, raw_faces_dir, final_csv, result_dir):
        self.temp_csv = temp_csv
        self.raw_faces_dir = raw_faces_dir
        self.final_csv = final_csv
        self.result_dir = result_dir

    def cleanup_faces(self):
        temp_faces_df = pd.read_csv(self.temp_csv)
        temp_faces_df = temp_faces_df[
            temp_faces_df['filename'].apply(lambda x: os.path.exists(os.path.join(self.raw_faces_dir, x)))]

        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)

        for face_file in temp_faces_df['filename']:
            shutil.move(os.path.join(self.raw_faces_dir, face_file), os.path.join(self.result_dir, face_file))

        self.update_permanent_csv(temp_faces_df)
        os.remove(self.temp_csv)
        print("Очистка и перенос файлов завершены.")

    def update_permanent_csv(self, temp_faces_df):
        if os.path.exists(self.final_csv):
            permanent_faces_df = pd.read_csv(self.final_csv)
            permanent_faces_df = pd.concat([permanent_faces_df, temp_faces_df], ignore_index=True)
        else:
            permanent_faces_df = temp_faces_df
        permanent_faces_df.to_csv(self.final_csv, index=False)


@click.command()
@click.option('--video-dir', default='downloaded_video', help='Папка с локальными видео.')
@click.option('--raw-faces-dir', default='raw_faces', help='Папка для сохранения сырых изображений лиц.')
@click.option('--result-faces-dir', default='result_faces', help='Папка для сохранения итоговых изображений лиц.')
@click.option('--permanent-csv-file', default='faces.csv', help='CSV файл для хранения данных о лицах.')
def main(video_dir, raw_faces_dir, result_faces_dir, permanent_csv_file):
    while True:
        temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")

        try:
            video_downloader = choose_video_downloader(video_dir)
            video_path = video_downloader.download()

            is_deepfake = click.prompt('Выбери тип видео (1 - дипфейк, 2 - обычное)', type=int, default=2) == 1

            face_extractor = FaceExtractor(video_path, raw_faces_dir, is_deepfake)
            face_extractor.process_video()
            face_extractor.save_face_data(temp_csv_file)
            os.remove(video_path)

            open_folder(raw_faces_dir)
            click.prompt("Удалите ненужные изображения из папки raw_faces и нажмите Enter для продолжения", type=str,
                         default="")

            cleanup_manager = FaceCleanupManager(temp_csv_file, raw_faces_dir, permanent_csv_file, result_faces_dir)
            cleanup_manager.cleanup_faces()
        except Exception as err:
            print(err)
        finally:
            print('Начинаем сначала')


def choose_video_downloader(video_dir):
    is_youtube_video = click.prompt(
        'Выбери 1 для обработки видео с YouTube, 2 для обработки заранее загруженного видео', type=int,
        default=1) == 1
    if is_youtube_video:
        youtube_link = click.prompt('Ссылка на видео: ', type=str)
        return YouTubeVideoDownloader(video_dir, youtube_link)
    else:
        video_filename = click.prompt(f'Введи название видео в папке {video_dir}', type=str)
        return LocalVideoDownloader(video_dir, video_filename)


def open_folder(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        os.system(f"open {path}")
    elif platform.system() == "Linux":
        os.system(f"xdg-open {path}")
    else:
        print(f"Операционная система {platform.system()} не поддерживается.")


if __name__ == "__main__":
    main()
