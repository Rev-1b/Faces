import os
import tempfile
import uuid

import click

from image_parsers import FaceRecognitionExtractor, HaarcascadesExtractor, DeepFaceExtractor
from image_savers import FaceCleanup
from utils import choose_video_downloader, open_folder, choose_folder


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

            # В этом месте выбираем, каким обработчиком изображения пользоваться
            face_extractor = FaceRecognitionExtractor(video_path, video_name, raw_photos_dir, is_deepfake)
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
    main()


login = 'wolftau'
password = 'wtal997'
