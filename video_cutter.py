import cv2
from moviepy.video.io.VideoFileClip import VideoFileClip

# Глобальные переменные для хранения координат
rect = []
cropping = False


def crop_video_frame(event, x, y, flags, param):
    global rect, cropping

    if event == cv2.EVENT_LBUTTONDOWN:
        rect = [(x, y)]
        cropping = True

    elif event == cv2.EVENT_LBUTTONUP:
        rect.append((x, y))
        cropping = False
        cv2.rectangle(image, rect[0], rect[1], (0, 255, 0), 2)
        cv2.imshow("image", image)


def crop_video(input_path, output_path):
    if len(rect) == 2:
        x1, y1 = rect[0]
        x2, y2 = rect[1]

        with VideoFileClip(input_path) as clip:
            cropped_clip = clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
            cropped_clip.write_videofile(output_path, codec="libx264")


# Загружаем видео и выбираем первый кадр для кадрирования
input_video = "input_video.mp4"
output_video = "cropped_video.mp4"

with VideoFileClip(input_video) as clip:
    frame = clip.get_frame(0)  # Получаем первый кадр видео
    image = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

cv2.imshow("image", image)
cv2.setMouseCallback("image", crop_video_frame)

# Ожидаем, пока пользователь выберет область и нажмет любую клавишу
cv2.waitKey(0)

# Закрываем все окна
cv2.destroyAllWindows()

# Кадрируем и сохраняем видео
if rect:
    crop_video(input_video, output_video)
    print(f"Видео сохранено: {output_video}")
else:
    print("Область для кадрирования не выбрана.")
