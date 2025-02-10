import zipfile
import os
import plistlib
import json
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Button, Label, Frame, Progressbar
from PIL import Image

############################################################
#           1) PNG -> BMP (含分辨率检查 & WRONGSIZE)
############################################################

def convert_png_to_bmp(source_dir, target_dir):
    """
    递归扫描 source_dir 下所有子目录的 .png 文件，转换为 8位灰度 BMP。
    若分辨率 > 1024 则先缩放至 1024×1024；
    若分辨率不在 (256,256)|(512,512)|(1024,1024)，则移到 WRONGSIZE 文件夹。
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    wrong_size_dir = os.path.join(target_dir, 'WRONGSIZE')
    if not os.path.exists(wrong_size_dir):
        os.makedirs(wrong_size_dir)

    supported_resolutions = {(256, 256), (512, 512), (1024, 1024)}

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith('.png'):
                file_path = os.path.join(root, file)
                with Image.open(file_path) as img:
                    img = img.convert('L')
                    # 若超过 1024x1024，则先缩放
                    if img.size[0] > 1024 or img.size[1] > 1024:
                        img = img.resize((1024, 1024), Image.LANCZOS)

                    base_filename = os.path.splitext(file)[0]
                    if img.size in supported_resolutions:
                        target_file_path = os.path.join(target_dir, f"{base_filename}.bmp")
                        img.save(target_file_path, 'BMP')
                    else:
                        wrong_file_path = os.path.join(wrong_size_dir, f"WARNING_{base_filename}.bmp")
                        img.save(wrong_file_path, 'BMP')

    print(f">>> PNG -> BMP 完成：{source_dir}")
    print("    若有分辨率不在(256,512,1024)之列的图片，已移入 WRONGSIZE 子目录。")


def resize_bmp_images(folder_path):
    """
    遍历指定文件夹中的所有.bmp文件，将分辨率超过1024×1024的图片再次压缩为1024×1024。
    """
    if not os.path.exists(folder_path):
        print(f">>> 未找到 {folder_path} 文件夹，无需进一步压缩。")
        return

    target_resolution = (1024, 1024)
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.bmp'):
            file_path = os.path.join(folder_path, filename)
            with Image.open(file_path) as img:
                if img.size[0] > 1024 or img.size[1] > 1024:
                    resized_image = img.resize(target_resolution, Image.LANCZOS)
                    resized_image.save(file_path, 'BMP')
                    print(f"图像已缩放并保存：{file_path}")
                else:
                    print(f"图像分辨率未超过 1024x1024：{file_path}")


############################################################
#     2) 查找 BMP 并复制默认 .ini 文件 (若不存在则复制)
############################################################

def find_bmp_files(source_dir):
    """
    遍历指定目录和子目录，收集所有BMP文件的路径。
    """
    bmp_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith('.bmp'):
                bmp_files.append(os.path.join(root, file))
    return bmp_files

def copy_ini_files(bmp_files, ini_source):
    """
    为每个BMP文件复制并重命名INI文件到相应的文件夹，除非INI文件已存在。
    需要在 ./defult/ 下存在 default.ini (或对应名称)。
    """
    ini_path = os.path.join('./defult', ini_source)
    if not os.path.exists(ini_path):
        print(f"未找到指定的INI文件: {ini_path}")
        return

    for bmp_file in bmp_files:
        directory = os.path.dirname(bmp_file)
        bmp_base_name = os.path.splitext(os.path.basename(bmp_file))[0]
        ini_target_path = os.path.join(directory, f"{bmp_base_name}.ini")

        if os.path.exists(ini_target_path):
            print(f"INI文件已存在，跳过: {ini_target_path}")
            continue

        shutil.copy(ini_path, ini_target_path)
        print(f"Copied and renamed INI file to {ini_target_path}")

def assign_ini_to_bmp_in_folder(folder):
    """
    在给定的 folder 目录(含子目录)中查找所有 .bmp 文件，为其复制INI。
    """
    bmp_files = find_bmp_files(folder)
    ini_file_name = 'default.ini'  # 确保 ./defult/default.ini 存在
    copy_ini_files(bmp_files, ini_file_name)


############################################################
#    3) 将 PNG/JPG 拷贝到 texture_shape 的自动整理函数
############################################################

def collect_image_files(source_dir, extensions=None):
    if extensions is None:
        extensions = ['.png', '.jpg', '.jpeg']
    png_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                png_files.append(os.path.join(root, file))
    return png_files

def ensure_unique_filename(base_name, ext, existing_files):
    counter = 1
    new_file_path = f"{base_name}{ext}"
    while new_file_path in existing_files:
        new_file_path = f"{base_name}_{counter}{ext}"
        counter += 1
    return new_file_path

def copy_files_to_new_folder(files, target_dir, folder_name):
    target_subdir = os.path.join(target_dir, folder_name)
    if not os.path.exists(target_subdir):
        os.makedirs(target_subdir)

    existing_files = set()
    for idx, file_path in enumerate(files):
        new_filename = f"{folder_name}_{idx + 1}{os.path.splitext(file_path)[1]}"
        final_path = os.path.join(target_subdir, new_filename)
        final_path = ensure_unique_filename(os.path.splitext(final_path)[0],
                                            os.path.splitext(final_path)[1],
                                            existing_files)
        try:
            shutil.copy2(file_path, final_path)
            existing_files.add(final_path)
        except IOError as e:
            print(f"无法复制文件 {file_path} 到 {final_path}: {e}")

def extract_folder_name(source_dir):
    base_name = os.path.basename(source_dir)
    folder_name, _ = os.path.splitext(base_name)
    return folder_name

def auto_process_images(source_dir, target_dir):
    """
    用于把解压得到的 PNG/JPG 文件复制到指定目标目录下，避免重复命名冲突。
    """
    try:
        folder_name = extract_folder_name(source_dir)
        image_files = collect_image_files(source_dir)
        if not image_files:
            print("未找到任何符合条件的图片文件。")
            return
        copy_files_to_new_folder(image_files, target_dir, folder_name)
        print(f"所有图片文件已成功复制到 {os.path.join(target_dir, folder_name)}")
    except Exception as e:
        print(f"处理文件时发生错误: {e}")


############################################################
#         4) 解析 .brushset（只提取 .png/.archive）
############################################################

class BrushsetParser:
    """
    Parse archived textures of Procreate brushes, extracting .png & .archive files.
    不做自动 BMP 转换。
    """
    def __init__(self, filename, progress_callback=None):
        self.filename = filename
        self.progress_callback = progress_callback
        print(f"Initialized parser with file: {filename}")

    def check(self):
        return zipfile.is_zipfile(self.filename)

    def parse(self):
        """
        解压并提取 .png & .archive 文件到 cache/<文件名>.brushset
        并把提取到的 PNG/JPG 复制到 ./texture_shape
        """
        with zipfile.ZipFile(self.filename) as archive:
            namelist = archive.namelist()
            brushset_name = os.path.splitext(os.path.basename(self.filename))[0] + ".brushset"
            base_directory = os.path.join('cache', brushset_name)

            if not os.path.exists(base_directory):
                os.makedirs(base_directory)

            total_files = len(namelist)
            for idx, member in enumerate(namelist):
                # 忽略以下文件夹
                if any(folder in member for folder in ("AuthorPicture/", "QuickLook/", "Signature/")):
                    continue

                if 'Reset' in member:
                    continue

                dirname = os.path.dirname(member)
                full_dir = os.path.join(base_directory, dirname)
                if not os.path.exists(full_dir):
                    os.makedirs(full_dir)

                if member.endswith('.png'):
                    out_path = os.path.join(base_directory, member)
                    with archive.open(member) as f:
                        img = Image.open(f)
                        img.save(out_path)
                elif member.endswith('.archive'):
                    out_path = os.path.join(base_directory, member)
                    with archive.open(member) as f:
                        params = plistlib.load(f)
                    resolved_params = self.resolve_uids(params.get('$objects', []),
                                                        params.get('$objects', [])[1])
                    params_file_name = os.path.splitext(out_path)[0] + '_resolved_params.json'
                    resolved_params = self.handle_bundled_textures(resolved_params, params_file_name)
                    with open(params_file_name, 'w', encoding='utf-8') as json_file:
                        json.dump(resolved_params, json_file, indent=4)

                # 更新进度
                if self.progress_callback:
                    self.progress_callback((idx+1) / total_files * 100)

        # 将 PNG 文件复制到 ./texture_shape/<brushsetName>.brushset/
        auto_process_images(base_directory, './texture_shape')

    def handle_bundled_textures(self, params, params_file_name):
        keys_to_check = ['bundledGrainPath', 'bundledShapePath']
        base_dir = os.path.dirname(params_file_name)
        for key in keys_to_check:
            if key not in params:
                continue

            if params[key] != '$null':
                src_path = os.path.join("images", os.path.basename(params[key]))
                dst_path = os.path.join(base_dir, os.path.basename(params[key]))
                if os.path.exists(src_path):
                    shutil.copy(src_path, dst_path)
                else:
                    print(f"[Warning] {src_path} not found, skip copying.")
            else:
                print(f"{key} is '$null'; trying default image path.")
                default_image = key.replace('bundled', '').replace('Path', '') + ".png"
                default_image_path = os.path.join(base_dir, default_image)
                if os.path.exists(default_image_path):
                    params[key] = default_image
                else:
                    print(f"Default image {default_image_path} not found.")
        return params

    def resolve_uids(self, objects, obj):
        if isinstance(obj, plistlib.UID):
            return self.resolve_uids(objects, objects[obj.data])
        elif isinstance(obj, dict):
            return {k: self.resolve_uids(objects, v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [self.resolve_uids(objects, item) for item in obj]
        elif isinstance(obj, bytes):
            return obj.hex()
        else:
            return obj


############################################################
#                     Tkinter 界面
############################################################

def browse_brushset(progress_label, progress_bar):
    """
    解析 .brushset 文件，只提取 .png & .archive，
    并复制图像文件到 texture_shape 文件夹
    """
    filenames = filedialog.askopenfilenames(filetypes=[("Procreate Brushset", "*.brushset")])
    if not filenames:
        return

    for filename in filenames:
        parser = BrushsetParser(
            filename,
            progress_callback=lambda prog: update_progress(prog, progress_label, progress_bar)
        )
        if parser.check():
            messagebox.showinfo("Info", f"开始解析：{os.path.basename(filename)}")
            parser.parse()
            messagebox.showinfo(
                "Success",
                f"解析已完成: {os.path.basename(filename)}\n"
                f"请查看 cache/ 与 texture_shape/ 文件夹。"
            )
            reset_progress(progress_label, progress_bar)
        else:
            messagebox.showerror("Error", f"{os.path.basename(filename)} 不是有效的 .brushset 文件。")

def browse_folders_for_bmp_and_ini():
    """
    允许用户多次选择文件夹；对每个文件夹中的 .png 文件进行 BMP 转换，
    然后对生成的 BMP 文件复制 & 重命名 .ini 文件（如果不存在）。
    """
    selected_folders = []
    while True:
        folder = filedialog.askdirectory(title="Select a folder (Cancel to stop choosing)")
        if not folder:
            break  # 用户取消或关闭
        selected_folders.append(folder)

    if not selected_folders:
        return  # 用户没有选择任何文件夹

    for folder in selected_folders:
        # 第一步：PNG -> BMP
        bmp_target_dir = os.path.join(folder, 'bmp')
        convert_png_to_bmp(folder, bmp_target_dir)

        # 可选：再次压缩 WRONGSIZE
        wrong_size_dir = os.path.join(bmp_target_dir, 'WRONGSIZE')
        resize_bmp_images(wrong_size_dir)

        # 第二步：为生成的 BMP 文件复制对应 .ini
        assign_ini_to_bmp_in_folder(bmp_target_dir)

    messagebox.showinfo("Success", "BMP 转换 + INI 复制已完成，请查看每个所选文件夹下的 bmp/ 子目录。")


def invert_selected_bmp_files():
    """
    允许用户多选 .bmp 文件，对每一个执行反相处理，
    结果保存到同目录下的 invert 子文件夹，文件名添加前缀 '_'
    """
    bmp_paths = filedialog.askopenfilenames(
        filetypes=[("BMP Files", "*.bmp")],
        title="Select BMP files to invert"
    )
    if not bmp_paths:
        return

    for bmp_file in bmp_paths:
        src_dir = os.path.dirname(bmp_file)
        invert_dir = os.path.join(src_dir, "invert")
        if not os.path.exists(invert_dir):
            os.makedirs(invert_dir)

        filename = os.path.basename(bmp_file)
        out_path = os.path.join(invert_dir, f"_{filename}")

        with Image.open(bmp_file) as img:
            # 反相处理：点变换 255 - p
            inverted_image = img.point(lambda p: 255 - p)
            inverted_image.save(out_path)

        print(f"反相图像已保存到：{out_path}")

    messagebox.showinfo("Success", "所选BMP文件已完成反相处理，并存储到各自文件夹的 invert/ 子目录。")


def update_progress(progress, label, progress_bar):
    progress_bar["value"] = progress
    label.config(text=f"Progress: {int(progress)}%")
    label.update()

def reset_progress(label, progress_bar):
    progress_bar["value"] = 0
    label.config(text="Progress: 0%")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Procreate Brushset Parser + BMP + INI + Invert")
    root.geometry("650x420")
    root.configure(bg="#2b2b2b")

    frame = Frame(root, style="TFrame")
    frame.pack(expand=True)

    info_label = Label(
        frame,
        text=("1) 解析 .brushset 文件以提取PNG到 cache/ 与 texture_shape/\n"
              "2) 'Convert to BMP & INI': 多次选文件夹，对 .png => .bmp 并赋予 .ini\n"
              "3) 'Invert BMP Files': 多选 BMP，对每张图片执行反相处理，"
              "   并保存到同目录下的 invert/ 子文件夹"),
        foreground="white",
        background="#2b2b2b",
        font=("Helvetica", 12),
        justify="left"
    )
    info_label.pack(pady=10)

    progress_label = Label(
        frame,
        text="Progress: 0%",
        foreground="white",
        background="#2b2b2b",
        font=("Helvetica", 10)
    )
    progress_label.pack(pady=5)

    progress_bar = Progressbar(frame, orient="horizontal", length=500, mode="determinate")
    progress_bar.pack(pady=10)

    # 按钮1：解析 .brushset
    parse_button = Button(frame, text="Parse .brushset", command=lambda: browse_brushset(progress_label, progress_bar))
    parse_button.pack(pady=5)

    # 按钮2：文件夹 -> PNG => BMP + 复制 .ini
    convert_button = Button(frame, text="Convert to BMP & INI", command=browse_folders_for_bmp_and_ini)
    convert_button.pack(pady=5)

    # 按钮3：多选 BMP 文件 -> 反相处理
    invert_button = Button(frame, text="Invert BMP Files", command=invert_selected_bmp_files)
    invert_button.pack(pady=5)

    root.mainloop()
