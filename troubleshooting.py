import os
import pandas as pd


class MetaValidator:
    def __init__(self, meta_file: str, images_root: str):
        self.meta_file = meta_file
        self.images_root = images_root
        self.meta_df = pd.read_csv(self.meta_file)
        a = 0

    def validate_images(self):
        # Получаем список всех изображений в папке
        all_images = self.get_all_images(self.images_root)
        meta_image_paths = set(self.meta_df['filepath'].values)

        # Проверяем, есть ли соответствующая запись в meta.csv для каждого изображения
        missing_images = []
        for image_path in all_images:
            # relative_path = os.path.relpath(image_path, self.images_root)
            if image_path not in meta_image_paths:
                missing_images.append(image_path)

        return missing_images

    def get_all_images(self, root_dir):
        image_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')  # Допустимые расширения
        image_paths = []

        for subdir, _, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith(image_extensions):
                    image_paths.append(os.path.join(subdir, file))

        return image_paths

    def report_missing_images(self, output_file):
        missing_images = self.validate_images()
        if missing_images:
            print(f"Найдено {len(missing_images)} изображений без записи в meta.csv:")
            with open(output_file, 'w', encoding='utf-8') as f:
                for img in missing_images:
                    f.write(img + '\n')
        else:
            print("Все изображения имеют соответствующие записи в meta.csv.")


class VideoChecker:
    def __init__(self, images_file: str, videos_root: str):
        self.images_file = images_file
        self.videos_root = videos_root
        self.deepfake_count = 0
        self.normal_count = 0

    def check_videos(self):
        with open(self.images_file, 'r', encoding='utf-8') as f:
            missing_images = f.readlines()

        # Извлекаем названия видео из имен изображений
        video_names = {self.extract_video_name(os.path.basename(img.strip())) for img in missing_images}

        # Проверяем, в какой папке находится каждое видео
        for video_name in video_names:
            if self.is_video_deepfake(video_name):
                self.deepfake_count += 1
            else:
                self.normal_count += 1

    def extract_video_name(self, image_name: str):
        return image_name.split('_')[0]  # Извлекаем первый UUID из имени изображения

    def is_video_deepfake(self, video_name: str):
        deepfake_video_path = os.path.join(self.videos_root, 'deepfake', f"{video_name}.mp4")
        normal_video_path = os.path.join(self.videos_root, 'normal', f"{video_name}.mp4")
        return os.path.exists(deepfake_video_path)

    def report_statistics(self):
        print(f"Количество видео в папке deepfake: {self.deepfake_count}")
        print(f"Количество видео в папке normal: {self.normal_count}")


class MetaCreator:
    def __init__(self, images_file: str, videos_root: str, output_file: str):
        self.images_file = images_file
        self.videos_root = videos_root
        self.output_file = output_file
        self.meta_data = []

    def create_new_meta(self):
        with open(self.images_file, 'r', encoding='utf-8') as f:
            missing_images = f.readlines()

        for img in missing_images:
            img = img.strip()
            video_name = self.extract_video_name(os.path.basename(img))

            # Проверяем, в какой папке находится видео
            is_deepfake = self.is_video_deepfake(video_name)
            self.meta_data.append({
                "filepath": img,
                "deepfake": is_deepfake
            })

        # Сохраняем новый meta файл в формате CSV
        self.save_meta_to_csv()

    def extract_video_name(self, image_name: str):
        return image_name.split('_')[0]  # Извлекаем первый UUID из имени изображения

    def is_video_deepfake(self, video_name: str):
        deepfake_video_path = os.path.join(self.videos_root, 'deepfake', f"{video_name}.mp4")
        return os.path.exists(deepfake_video_path)

    def save_meta_to_csv(self):
        # Создаем DataFrame из списка метаданных и сохраняем в CSV
        df = pd.DataFrame(self.meta_data)
        df.to_csv(self.output_file, index=False)
        print(f"Новый meta файл сохранен: {self.output_file}")


def check_photos_in_meta(video_name: str, meta_file: str) -> bool:
    # Загружаем метаданные из CSV-файла
    try:
        meta_df = pd.read_csv(meta_file)
    except FileNotFoundError:
        print(f"Файл {meta_file} не найден.")
        return False

    # Извлекаем имена фотографий, соответствующие видео
    photos = meta_df[meta_df['filepath'].str.contains(video_name)]['filepath'].tolist()

    if photos:
        print(f"Найдено {len(photos)} фото(а) для видео '{video_name}':")
        for photo in photos:
            print(photo)
        return True
    else:
        print(f"Фото для видео '{video_name}' не найдено.")
        return False


def append_meta(meta_file, new_meta_file, output_file):
    """Добавляет содержимое new_meta в конец meta и сохраняет результат в output_file"""
    # Чтение двух файлов CSV
    meta_df = pd.read_csv(meta_file)
    new_meta_df = pd.read_csv(new_meta_file)

    # Добавление строк из new_meta_df в meta_df
    combined_df = pd.concat([meta_df, new_meta_df], ignore_index=True)

    # Сохранение результата в output_file
    combined_df.to_csv(output_file, index=False)

if __name__ == "__main__":
    # Укажите путь к вашему meta.csv и папке с изображениями
    # meta_file_path = 'meta.csv'
    # images_root_path = 'photos'
    # validator = MetaValidator(meta_file_path, images_root_path)
    # validator.report_missing_images('bruh')

    # images_file_path = 'bruh'  # Путь к файлу с пропущенными изображениями
    # videos_root_path = 'videos'  # Путь к папке с видео
    # checker = VideoChecker(images_file_path, videos_root_path)
    # checker.check_videos()
    # checker.report_statistics()

    # Укажите путь к файлу с пропущенными изображениями, корневой папке с видео и выходному файлу
    images_file_path = 'bruh'  # Путь к файлу с пропущенными изображениями
    videos_root_path = 'videos'  # Путь к папке с видео
    output_meta_file = 'new_meta.csv'  # Путь к новому файлу meta

    creator = MetaCreator(images_file_path, videos_root_path, output_meta_file)
    creator.create_new_meta()

    # video_name_input = '6ef065a8-284a-4347-a54a-6d15b2c29ba6'
    # meta_file_path = 'meta.csv'  # Путь к файлу meta.csv
    #
    # check_photos_in_meta(video_name_input, meta_file_path)