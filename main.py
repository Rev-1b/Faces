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
from collections import namedtuple


Video = namedtuple('Video', ['path', 'name'])


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
        video_filename = f"{uuid.uuid4()}.mp4"
        output_path = os.path.join(self.output_dir, video_filename)
        video_stream.download(output_path=self.output_dir, filename=video_filename)
        print("\nЗагрузка завершена!")
        return Video(output_path, video_filename)


class LocalVideoDownloader(VideoDownloader):
    def __init__(self, output_dir, video_filename):
        super().__init__(output_dir)
        self.video_filename = video_filename

    def download(self):
        video_path = os.path.join(self.output_dir, self.video_filename)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видео {self.video_filename} не найдено в папке {self.output_dir}.")
        return Video(video_path, self.video_filename)

# ----------------------------------------------------------------------------------------------------------------------


class SaveMixin:
    def save(self, face_image, video_name: str, output_dir):
        face_filename = f"{video_name.rstrip('.mp4')}_{uuid.uuid4()}.jpg"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        cv2.imwrite(os.path.join(output_dir, face_filename), face_image)
        return face_filename


class FaceExtractor(SaveMixin):
    def __init__(self, video_path, video_name, output_dir, deepfake, frame_skip=0):
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


class FaceCleanup:
    def __init__(self, temp_csv, raw_faces_dir, final_csv, result_dir):
        self.temp_csv = temp_csv
        self.raw_faces_dir = raw_faces_dir
        self.final_csv = final_csv
        self.result_dir = result_dir

    def cleanup_faces(self):
        temp_faces_df = pd.read_csv(self.temp_csv)
        temp_faces_df = temp_faces_df[
            temp_faces_df['filepath'].apply(lambda x: os.path.exists(os.path.join(self.raw_faces_dir, x)))]

        if not os.path.exists(self.result_dir):
            os.makedirs(self.result_dir)

        for face_file in temp_faces_df['filepath']:
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
@click.option('--normal-video-dir', default=os.path.join('videos', 'normal'), help='Папка с нормальными видео.')
@click.option('--deepfake-video-dir', default=os.path.join('videos', 'deepfake'), help='Папка с дипфейками.')
@click.option('--raw_photos-dir', default='raw_photos', help='Папка для сохранения сырых изображений лиц.')
@click.option('--photos-dir', default='photos', help='Папка для сохранения итоговых изображений лиц.')
@click.option('--permanent-csv-file', default='meta.csv', help='CSV файл для хранения данных о лицах.')
def main(normal_video_dir, deepfake_video_dir, raw_photos_dir, photos_dir, permanent_csv_file):
    while True:
        temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")

        try:
            is_deepfake = click.prompt(
                'Выберите тип видео',
                type=click.Choice(['Deepfake', 'Normal'], case_sensitive=False),
                show_choices=True,
                default='Normal'
            ) == 'Deepfake'

            video_dir = deepfake_video_dir if is_deepfake else normal_video_dir
            video_downloader = choose_video_downloader(video_dir)
            video_path, video_name = video_downloader.download()

            face_extractor = FaceExtractor(video_path, video_name, raw_photos_dir, is_deepfake)
            face_extractor.process_video()
            face_extractor.save_face_data(temp_csv_file)

            open_folder(raw_photos_dir)
            click.prompt("Удалите ненужные изображения из папки raw_faces и нажмите Enter для продолжения", type=str,
                         default="")

            folder = choose_folder()
            full_output_dir = os.path.join(photos_dir, folder)

            cleanup_manager = FaceCleanup(temp_csv_file, raw_photos_dir, permanent_csv_file, full_output_dir)
            cleanup_manager.cleanup_faces()
        except Exception as err:
            print(err)
        finally:
            print('Начинаем сначала')


def choose_video_downloader(video_dir):
    choice = click.prompt(
        'Выберите источник видео',
        type=click.Choice(['Youtube', 'Local'], case_sensitive=False),
        show_choices=True,
        default='Youtube'
    )
    if choice == 'Youtube':
        youtube_link = click.prompt('Ссылка на видео', type=str)
        return YouTubeVideoDownloader(video_dir, youtube_link)
    else:
        video_filename = click.prompt(f'Введите название видео в папке {video_dir}', type=str)
        return LocalVideoDownloader(video_dir, video_filename)


def choose_folder():
    folders = {
        '1': 'men/black',
        '2': 'men/white',
        '3': 'men/asian',
        '4': 'women/black',
        '5': 'women/white',
        '6': 'women/asian'
    }
    folder_choice = click.prompt(
        'Выбери папку для сохранения изображений: \n'
        '1 - men/black\n'
        '2 - men/white\n'
        '3 - men/asian\n'
        '4 - women/black\n'
        '5 - women/white\n'
        '6 - women/asian',
        type=str
    )
    return folders.get(folder_choice, 'men/white')


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
