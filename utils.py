import os.path
import sys
from pathlib import Path

import click
import pandas as pd
from tqdm import tqdm


def safe_prompt(text, **kwargs):
    response = click.prompt(text, **kwargs)
    if isinstance(response, str) and response.lower() == 'exit':
        click.echo("Программа завершена.")
        sys.exit(0)
    return response


meta_file = 'meta.csv'
image_base_path = Path(meta_file).parent
video_folder = Path('./videos')
video_uuids = set()


class MetaProcessor:
    def __init__(self, meta_file, image_base_path, video_folders):
        self.meta_file = Path(meta_file)
        self.image_base_path = Path(image_base_path)
        self.video_folders = video_folders
        self.video_uuids = set()

    def process_meta(self):
        # Чтение meta.csv с помощью pandas
        df = pd.read_csv(self.meta_file)

        valid_rows = []
        undetected_files = 0

        # tqdm для отображения прогресса
        for index, row in tqdm(df.iterrows(), total=len(df), desc="Проверка изображений"):
            filepath = self.image_base_path / row['filepath']
            if filepath.exists():
                valid_rows.append(row)
                # Извлечение первого UUID из имени файла изображения
                video_uuid = row['filepath'].split('_')[0].split('\\')[-1]
                self.video_uuids.add(video_uuid)
            else:
                tqdm.write(f"\nФайл не найден: {filepath}", end='')
                undetected_files += 1

        # Создание нового DataFrame с существующими файлами
        new_df = pd.DataFrame(valid_rows, columns=df.columns)
        # Запись обратно в meta.csv
        new_df.to_csv(self.meta_file, index=False)
        print(f"Найдено {undetected_files} отсутствующих файлов")

    def clean_videos(self):
        # Удаление видео, не упомянутых в meta.csv
        undetected_files = 0
        video_files = [video for video_dir in self.video_folders for video in Path(video_dir).glob('*.mp4')]

        for video_file in tqdm(video_files, desc="Очистка видео"):
            video_uuid = video_file.stem
            if video_uuid not in self.video_uuids:
                tqdm.write(f"\nУдаление неиспользуемого видео: {video_file}", end='')
                # video_file.unlink()
                undetected_files += 1
        print(f'\n Найдено лишних видео: {undetected_files}')

    def run(self):
        self.process_meta()
        self.clean_videos()


if __name__ == "__main__":
    processor = MetaProcessor(
        meta_file='merged_meta.csv',
        image_base_path='.',
        video_folders=(
            os.path.join('videos', 'normal'),
            os.path.join('videos', 'deepfake'))
    )
    processor.run()
