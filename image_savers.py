import os
import shutil

import pandas as pd


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

        # Обновление значений в столбце 'filepath' путем добавления префикса
        temp_faces_df['filepath'] = temp_faces_df['filepath'].apply(lambda x: os.path.join(self.result_dir, x))

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