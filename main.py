import os

import click

from scripts import Config, script_list
from utils import safe_prompt


@click.command()
@click.option('--normal-video-dir', default=os.path.join('videos', 'normal'), help='Папка с нормальными видео.')
@click.option('--deepfake-video-dir', default=os.path.join('videos', 'deepfake'), help='Папка с дипфейками.')
@click.option('--temp-video-dir', default=os.path.join('videos', 'temp'),
              help='Временная папка с предзагруженными видео.')
@click.option('--raw_photos-dir', default='raw_photos', help='Папка для сохранения сырых изображений лиц.')
@click.option('--photos-dir', default='photos', help='Папка для сохранения итоговых изображений лиц.')
@click.option('--permanent-csv-file', default='meta.csv', help='CSV файл для хранения данных о лицах.')
@click.option('--links-file', default='links.txt', help='Файл со ссылками на видео.')
def main(normal_video_dir: str,
         deepfake_video_dir: str,
         temp_video_dir: str,
         raw_photos_dir: str,
         photos_dir: str,
         permanent_csv_file: str,
         links_file: str):
    config = Config(normal_video_dir, deepfake_video_dir,
                    temp_video_dir, raw_photos_dir, photos_dir,
                    permanent_csv_file, links_file)
    script_name = safe_prompt(
        text='\nВыберите, какой скрипт использовать:\n'
        '  manual     - Введите ссылку на YouTube или путь до локального видео вручную\n'
        '  links      - Автоматическая обработка YouTube ссылок из файла links\n'
        '  downloaded - Обработка видео из папки temp_videos\n',
        type=click.Choice(script_list.keys(), case_sensitive=False),
        default='manual',
        show_choices=False,
    )
    script = script_list[script_name](config)
    script.execute_script()


if __name__ == "__main__":
    main()
