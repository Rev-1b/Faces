import os
import platform

import click

from video_loaders import YouTubeVideoDownloader, LocalVideoDownloader


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
        '1': os.path.join('men', 'black'),
        '2': os.path.join('men', 'white'),
        '3': os.path.join('men', 'asian'),
        '4': os.path.join('women', 'black'),
        '5': os.path.join('women', 'white'),
        '6': os.path.join('women', 'asian'),
    }
    folder_choice = click.prompt(
        f'Выбери папку для сохранения изображений: \n'
        f'{(f"{key} - {value}\n" for key, value in folders.items())}',
        type=str
    )
    return folders.get(folder_choice)


def open_folder(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        os.system(f"open {path}")
    elif platform.system() == "Linux":
        os.system(f"xdg-open {path}")
    else:
        print(f"Операционная система {platform.system()} не поддерживается.")