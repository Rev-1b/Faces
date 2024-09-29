import os
import tempfile
import uuid
from collections import namedtuple

import click

from image_parsers import HaarcascadesExtractor
from image_savers import FaceCleanup
from utils import choose_video_downloader, open_folder, choose_folder
from video_loaders import YouTubeVideoDownloader, PreloadedVideoDownloader

Config = namedtuple('Config', [
    'normal_video_dir',
    'deepfake_video_dir',
    'temp_video_dir',
    'raw_photos_dir',
    'photos_dir',
    'permanent_csv_file',
    'links_file'
])


class BaseScript:
    def __init__(self, config: Config):
        self.config = config

    def execute_script(self):
        raise NotImplementedError('You must implement this method')

    def process_and_cleanup(self, temp_csv_file, video_downloader, is_deepfake, crop, frame_skip):
        video_path, video_name = video_downloader.download()
        face_extractor = HaarcascadesExtractor(
            video_path, video_name, self.config.raw_photos_dir,
            is_deepfake, crop, frame_skip)

        face_extractor.process_video()
        face_extractor.save_face_data(temp_csv_file)

        open_folder(self.config.raw_photos_dir)
        click.prompt("Удалите ненужные изображения из папки raw_faces")

        folder = choose_folder()
        full_output_dir = os.path.join(self.config.photos_dir, folder)

        cleanup_manager = FaceCleanup(temp_csv_file, self.config.raw_photos_dir,
                                      self.config.permanent_csv_file, full_output_dir)
        cleanup_manager.cleanup_faces()


class ManualInput(BaseScript):
    def execute_script(self):
        is_deepfake = click.prompt(
            text='Выберите, видео какого типа вы будете обрабатывать',
            type=click.Choice(['Deepfake', 'Normal'], case_sensitive=False),
            default='Deepfake'
        ) == 'Deepfake'

        constant_frame_skip = click.prompt(
            text='Выберите, сколько кадров будет пропускаться у обрабатываемых видео.\n'
                 'Если вы хотите указывать количество пропускаемых кадров для каждого видео\n'
                 'индивидуально, оставьте пустой строку ввода',
            type=int,
            default=None,
            show_default=False,
        )

        while True:
            temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")
            try:
                video_dir = self.config.deepfake_video_dir if is_deepfake else self.config.normal_video_dir
                video_downloader = choose_video_downloader(video_dir)

                frame_skip = click.prompt(
                    text='Выберите, сколько кадров пропускать',
                    type=int,
                    default=10,
                ) if constant_frame_skip is None else constant_frame_skip

                # Как правило, обрезать изображение нужно только для дипфейк-видео, в которых производится сравнение
                # между оригиналом и дипфейком, притом что дипфейк всегда с правой стороны
                if is_deepfake:
                    crop = click.prompt(
                        text='Обрезать изображение так, чтобы осталась только правая половина?',
                        type=click.Choice(['Y', 'N'], case_sensitive=False),
                        default='N',
                    ) == 'Y'
                else:
                    crop = False

                self.process_and_cleanup(temp_csv_file, video_downloader, is_deepfake, crop, frame_skip)

            except Exception as err:
                print(err)
            finally:
                print('Начинаем сначала')


class LinksInput(BaseScript):
    def execute_script(self):
        is_deepfake = click.prompt(
            text='Выберите, видео какого типа вы будете обрабатывать',
            type=click.Choice(['Deepfake', 'Normal'], case_sensitive=False),
            default='Deepfake'
        ) == 'Deepfake'

        constant_frame_skip = click.prompt(
            text='Выберите, сколько кадров будет пропускаться у обрабатываемых видео.\n'
                 'Если вы хотите указывать количество пропускаемых кадров для каждого видео\n'
                 'индивидуально, оставьте пустой строку ввода',
            type=int,
            default=None,
            show_default=False,
        )
        with open(self.config.links_file, 'r') as file:
            links = file.readlines()

        # Проверка, что файл не пустой
        if not links:
            raise Exception('Файл с ссылками пустой.')

        for link in links:
            try:
                # Проверка на пустую строку
                if not link.strip():
                    print("Пустая строка в файле ссылок.")
                    continue

                # Разбиваем строку на компоненты
                parts = link.strip().split()
                if constant_frame_skip is None and (len(parts) < 2 or not parts[1].isdigit()):
                    print(f"Неверный формат строки: {link}. Ожидается два элемента (ссылка и frame_skip).")
                    continue

                video_url = parts[0]

                frame_skip = int(parts[1]) if constant_frame_skip is None else constant_frame_skip

                # Проверка, что директории существуют, если нет — создаём их
                for directory in [self.config.normal_video_dir, self.config.raw_photos_dir, self.config.photos_dir]:
                    if not os.path.exists(directory):
                        print(f"Создаём директорию: {directory}")
                        os.makedirs(directory)

                # Создаём временный CSV файл
                temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")

                self.process_and_cleanup(temp_csv_file, video_url, is_deepfake, False, frame_skip)

                # Успешная обработка — удаляем ссылку из файла
                with open(self.config.links_file, 'w') as file:
                    remaining_links = [l for l in links if l != link]
                    file.write('\n'.join(remaining_links))

            except Exception as err:
                print(err)
            finally:
                print('Обработка следующего видео')


def predownloaded_input_script(normal_video_dir, deepfake_video_dir, temp_video_dir, raw_photos_dir, photos_dir,
                               permanent_csv_file):
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

            face_extractor = HaarcascadesExtractor(video_path, video_name, raw_photos_dir, is_deepfake, crop,
                                                   frame_skip)
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


script_list = {
    'manual': manual_input_script,
    'links': link_file_input_script,
    'downloaded': predownloaded_input_script,
}
