import os
import platform
import tempfile
import uuid
from collections import namedtuple

import click

from image_parsers import HaarcascadesExtractor
from image_savers import FaceCleanup
from utils import safe_prompt
from video_loaders import YouTubeVideoDownloader, PreloadedVideoDownloader, LocalVideoDownloader

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

        self.open_folder(self.config.raw_photos_dir)
        safe_prompt("Удалите ненужные изображения из папки raw_faces", default='')

        folder = self.choose_folder()
        full_output_dir = os.path.join(self.config.photos_dir, folder)

        cleanup_manager = FaceCleanup(temp_csv_file, self.config.raw_photos_dir,
                                      self.config.permanent_csv_file, full_output_dir)
        cleanup_manager.cleanup_faces()

    @staticmethod
    def open_folder(path):
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            os.system(f"open {path}")
        elif platform.system() == "Linux":
            os.system(f"xdg-open {path}")
        else:
            print(f"Операционная система {platform.system()} не поддерживается.")

    @staticmethod
    def choose_folder():
        folders = {
            '1': os.path.join('men', 'black'),
            '2': os.path.join('men', 'white'),
            '3': os.path.join('men', 'asian'),
            '4': os.path.join('women', 'black'),
            '5': os.path.join('women', 'white'),
            '6': os.path.join('women', 'asian'),
        }
        folder_choice = safe_prompt(
            text=f'\nВыбери папку для сохранения изображений: \n'
            f'{('\n'.join(f"{key} - {value}\n" for key, value in folders.items()))}',
            type=str
        )
        return folders.get(folder_choice)


class ManualInput(BaseScript):
    def execute_script(self):
        is_deepfake = safe_prompt(
            text='\nВыберите, видео какого типа вы будете обрабатывать',
            type=click.Choice(['Deepfake', 'Normal'], case_sensitive=False),
            default='Deepfake'
        ) == 'Deepfake'

        constant_frame_skip = safe_prompt(
            text='\nВыберите, сколько кадров будет пропускаться у обрабатываемых видео.\n'
                 'Если вы хотите указывать количество пропускаемых кадров для каждого видео '
                 'индивидуально, оставьте пустой строку ввода',
            type=str,
            default='',
            show_default=False,
        )
        constant_frame_skip = int(constant_frame_skip) if constant_frame_skip.isdigit() else None

        while True:
            temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")
            try:
                video_dir = self.config.deepfake_video_dir if is_deepfake else self.config.normal_video_dir
                video_downloader = self.choose_video_downloader(video_dir)

                frame_skip = safe_prompt(
                    text='Выберите, сколько кадров пропускать',
                    type=int,
                    default=10,
                ) if constant_frame_skip is None else constant_frame_skip

                # Как правило, обрезать изображение нужно только для дипфейк-видео, в которых производится сравнение
                # между оригиналом и дипфейком, притом что дипфейк всегда с правой стороны
                if is_deepfake:
                    crop = safe_prompt(
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

    @staticmethod
    def choose_video_downloader(video_dir):
        choice = safe_prompt(
            '\nВыберите источник видео',
            type=click.Choice(['Youtube', 'Local'], case_sensitive=False),
            show_choices=True,
            default='Youtube'
        )
        if choice == 'Youtube':
            youtube_link = safe_prompt('Ссылка на видео', type=str)
            return YouTubeVideoDownloader(video_dir, youtube_link)
        else:
            video_filename = safe_prompt(f'Введите название видео в папке {video_dir}', type=str)
            return LocalVideoDownloader(video_dir, video_filename)


class LinksInput(BaseScript):
    def execute_script(self):
        is_deepfake = safe_prompt(
            text='Выберите, видео какого типа вы будете обрабатывать',
            type=click.Choice(['Deepfake', 'Normal'], case_sensitive=False),
            default='Deepfake'
        ) == 'Deepfake'

        constant_frame_skip = safe_prompt(
            text='Выберите, сколько кадров будет пропускаться у обрабатываемых видео.\n'
                 'Если вы хотите, чтобы для каждого видео было индивидуальное количество\n'
                 'пропускаемых кадров, они должны быть указаны в файле links. В этом случае\n'
                 'оставьте строку ввода пустой',
            type=int,
            default=None,
            show_default=False,
        )
        with open(self.config.links_file, 'r') as file:
            links = file.readlines()

        if not links:
            raise Exception('Файл с ссылками пустой.')

        for link in links:
            try:
                if not link.strip():
                    print("Пустая строка в файле ссылок.")
                    continue

                parts = link.strip().split()
                if constant_frame_skip is None and (len(parts) < 2 or not parts[1].isdigit()):
                    print(f"Неверный формат строки: {link}. Ожидается два элемента (ссылка и frame_skip).")
                    continue

                video_url = parts[0]

                frame_skip = int(parts[1]) if constant_frame_skip is None else constant_frame_skip

                for directory in [self.config.normal_video_dir, self.config.raw_photos_dir, self.config.photos_dir]:
                    if not os.path.exists(directory):
                        print(f"Создаём директорию: {directory}")
                        os.makedirs(directory)

                temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")
                self.process_and_cleanup(temp_csv_file, video_url, is_deepfake, False, frame_skip)

                with open(self.config.links_file, 'w') as file:
                    remaining_links = [remain_link for remain_link in links if remain_link != link]
                    file.write('\n'.join(remaining_links))

            except Exception as err:
                print(err)
            finally:
                print('Обработка следующего видео')


class DownloadedInput(BaseScript):
    def execute_script(self):
        is_deepfake = safe_prompt(
            text='Выберите, видео какого типа вы будете обрабатывать',
            type=click.Choice(['Deepfake', 'Normal'], case_sensitive=False),
            default='Deepfake'
        ) == 'Deepfake'

        constant_frame_skip = safe_prompt(
            text='Выберите, сколько кадров будет пропускаться у обрабатываемых видео.\n',
            type=int,
            default=10,
        )
        while True:
            temp_csv_file = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.csv")
            try:
                video_dir = self.config.deepfake_video_dir if is_deepfake else self.config.normal_video_dir
                video_downloader = PreloadedVideoDownloader(video_dir, self.config.temp_video_dir)

                if is_deepfake:
                    crop = safe_prompt(
                        text='Обрезать изображение так, чтобы осталась только правая половина?',
                        type=click.Choice(['Y', 'N'], case_sensitive=False),
                        default='N',
                    ) == 'Y'
                else:
                    crop = False

                self.process_and_cleanup(temp_csv_file, video_downloader, is_deepfake, crop, constant_frame_skip)

            except Exception as err:
                print(err)
            finally:
                print('Начинаем сначала')


script_list = {
    'manual': ManualInput,
    'links': LinksInput,
    'downloaded': DownloadedInput,
}
