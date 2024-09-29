import os
import tempfile
import uuid

import click

from image_parsers import FaceRecognitionExtractor, HaarcascadesExtractor, DeepFaceExtractor
from image_savers import FaceCleanup
from utils import choose_video_downloader, open_folder, choose_folder
from video_loaders import YouTubeVideoDownloader, PreloadedVideoDownloader


@click.command()
@click.option('--normal-video-dir', default=os.path.join('videos', 'normal'), help='Папка с нормальными видео.')
@click.option('--deepfake-video-dir', default=os.path.join('videos', 'deepfake'), help='Папка с дипфейками.')
@click.option('--raw_photos-dir', default='raw_photos', help='Папка для сохранения сырых изображений лиц.')
@click.option('--photos-dir', default='photos', help='Папка для сохранения итоговых изображений лиц.')
@click.option('--permanent-csv-file', default='meta.csv', help='CSV файл для хранения данных о лицах.')
def manual_input_script(normal_video_dir, deepfake_video_dir, raw_photos_dir, photos_dir, permanent_csv_file):
    while True:
        temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")

        try:
            # is_deepfake = click.prompt(
            #     'Выберите тип видео',
            #     type=click.Choice(['Deepfake', 'Normal'], case_sensitive=False),
            #     show_choices=True,
            #     default='Deepfake'
            # ) == 'Deepfake'

            is_deepfake = True

            video_dir = deepfake_video_dir if is_deepfake else normal_video_dir
            video_downloader = choose_video_downloader(video_dir)

            # frame_skip = click.prompt(
            #     'Выберите, сколько кадров пропускать',
            #     type=int,
            #     default=10,
            #     show_default=True
            # )

            crop = click.prompt(
                'Обрезать ли изображение?',
                type=click.Choice(['Y', 'N'], case_sensitive=False),
                default='N',
                show_default=True,
                show_choices=True
            ) == 'Y'

            frame_skip = 5

            video_path, video_name = video_downloader.download()

            face_extractor = HaarcascadesExtractor(video_path, video_name, raw_photos_dir, is_deepfake, crop, frame_skip)
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


@click.command()
@click.option('--normal-video-dir', default=os.path.join('videos', 'normal'), help='Папка с нормальными видео.')
@click.option('--deepfake-video-dir', default=os.path.join('videos', 'deepfake'), help='Папка с дипфейками.')
@click.option('--raw_photos-dir', default='raw_photos', help='Папка для сохранения сырых изображений лиц.')
@click.option('--photos-dir', default='photos', help='Папка для сохранения итоговых изображений лиц.')
@click.option('--permanent-csv-file', default='meta.csv', help='CSV файл для хранения данных о лицах.')
@click.option('--links-file', default='links.txt', help='Файл со ссылками на видео.')
def link_file_input_script(normal_video_dir, deepfake_video_dir, raw_photos_dir, photos_dir, permanent_csv_file, links_file):
    with open(links_file, 'r') as file:
        links = file.readlines()

    for link in links:
        try:
            print(link)
            # Разбиваем строку на ссылку и значение frame_skip
            if not link:
                break
            parts = link.strip().split()
            video_url = parts[0]
            frame_skip = int(parts[1])
            # frame_skip = 5

            temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")

            # Используем нормальную папку для всех видео
            video_downloader = YouTubeVideoDownloader(normal_video_dir, video_url)

            # Загружаем видео с использованием ссылки
            video_path, video_name = video_downloader.download()

            # Инициализируем и запускаем извлечение лиц
            face_extractor = HaarcascadesExtractor(video_path, video_name, raw_photos_dir, False, frame_skip)
            face_extractor.process_video()
            face_extractor.save_face_data(temp_csv_file)

            # Открываем папку для редактирования изображений
            open_folder(raw_photos_dir)
            click.prompt("Удалите ненужные изображения из папки raw_faces и нажмите Enter для продолжения", type=str,
                         default="")

            folder = choose_folder()
            full_output_dir = os.path.join(photos_dir, folder)

            cleanup_manager = FaceCleanup(temp_csv_file, raw_photos_dir, permanent_csv_file, full_output_dir)
            cleanup_manager.cleanup_faces()
        except Exception as err:
            print(f"Ошибка при обработке видео {video_url}: {err}")
        finally:
            print('Обработка следующего видео')


@click.command()
@click.option('--normal-video-dir', default=os.path.join('videos', 'normal'), help='Папка с нормальными видео.')
@click.option('--deepfake-video-dir', default=os.path.join('videos', 'deepfake'), help='Папка с дипфейками.')
@click.option('--temp-video-dir', default='temp_videos', help='Временная папка с предзагруженными видео.')
@click.option('--raw_photos-dir', default='raw_photos', help='Папка для сохранения сырых изображений лиц.')
@click.option('--photos-dir', default='photos', help='Папка для сохранения итоговых изображений лиц.')
@click.option('--permanent-csv-file', default='meta.csv', help='CSV файл для хранения данных о лицах.')
def predownloaded_input_script(normal_video_dir, deepfake_video_dir, temp_video_dir, raw_photos_dir, photos_dir, permanent_csv_file):
    while True:
        temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")
        try:
            is_deepfake = True
            video_dir = deepfake_video_dir if is_deepfake else normal_video_dir
            video_downloader = PreloadedVideoDownloader(video_dir, temp_video_dir)

            # crop = click.prompt(
            #     'Обрезать ли изображение?',
            #     type=click.Choice(['Y', 'N'], case_sensitive=False),
            #     default='N',
            #     show_default=True,
            #     show_choices=True
            # ) == 'Y'

            crop = False
            frame_skip = 5

            video_path, video_name = video_downloader.download()

            face_extractor = HaarcascadesExtractor(video_path, video_name, raw_photos_dir, is_deepfake, crop, frame_skip)
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


if __name__ == "__main__":
    manual_input_script()
