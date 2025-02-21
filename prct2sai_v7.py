import zipfile
import os
import plistlib
import json
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Button, Label, Frame, Progressbar
from PIL import Image
import glob
import sys
from PIL.Image import Resampling
from PIL.ImageTk import PhotoImage
#    pyinstaller --windowed --icon=bitbug_favicon.ico prct2sai_v7.py
############################################################
#           1) PNG -> BMP (含分辨率检查 & WRONGSIZE)
############################################################

def get_nearest_standard_size(width, height):
    """
    获取最接近的标准分辨率
    对于正方形图片，返回小于当前尺寸的最大标准分辨率
    """
    if width != height:
        return None
    
    standard_sizes = [256, 512, 1024]
    current_size = width  # 因为是正方形，width 等于 height
    
    # 找到小于当前尺寸的最大标准分辨率
    for size in reversed(standard_sizes):
        if current_size >= size:
            return (size, size)
    
    # 如果比256还小，返回None
    return None

def convert_png_to_bmp(source_dir, target_dir):
    """
    遍历指定目录下的所有图片文件，转换为BMP格式。
    支持的格式：PNG, JPG, JPEG, TIFF, BMP, GIF, WebP 等
    若分辨率 > 1024 则先缩放至 1024×1024；
    若是正方形但不是标准分辨率，则缩放至下一级标准分辨率；
    若分辨率不在 (256,256)|(512,512)|(1024,1024)，则移到 WRONGSIZE 文件夹。
    """
    from PIL import Image, ImageFilter
    from PIL.Image import Resampling

    # 支持的图片格式
    SUPPORTED_FORMATS = {
        '.png', '.jpg', '.jpeg', '.tiff', '.tif', 
        '.bmp', '.gif', '.webp', '.psd', '.ico'
    }

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    wrong_size_dir = os.path.join(target_dir, 'WRONGSIZE')
    if not os.path.exists(wrong_size_dir):
        os.makedirs(wrong_size_dir)

    supported_resolutions = {(256, 256), (512, 512), (1024, 1024)}

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in SUPPORTED_FORMATS:
                file_path = os.path.join(root, file)
                base_filename = os.path.splitext(file)[0]
                
                try:
                    with Image.open(file_path) as img:
                        # 如果是动图，只取第一帧
                        if hasattr(img, 'is_animated') and img.is_animated:
                            img.seek(0)
                        
                        # 转换为灰度图
                        img = img.convert('L')
                        original_size = img.size
                        
                        # 若超过 1024x1024，则先缩放
                        if img.size[0] > 1024 or img.size[1] > 1024:
                            img = img.resize((1024, 1024), Resampling.LANCZOS)
                            print(f"已将 {file} 从 {original_size} 压缩至 1024x1024")
                        # 若是正方形但不是标准分辨率，尝试缩放到下一级标准分辨率
                        elif img.size[0] == img.size[1] and img.size not in supported_resolutions:
                            nearest_size = get_nearest_standard_size(img.size[0], img.size[1])
                            if nearest_size:
                                img = img.resize(nearest_size, Resampling.LANCZOS)
                                print(f"已将 {file} 从 {original_size} 压缩至 {nearest_size}")

                        if img.size in supported_resolutions:
                            target_file_path = os.path.join(target_dir, f"{base_filename}.bmp")
                            img.save(target_file_path, 'BMP')
                            print(f"已转换: {file} -> {os.path.basename(target_file_path)}")
                        else:
                            wrong_file_path = os.path.join(wrong_size_dir, f"WARNING_{base_filename}.bmp")
                            img.save(wrong_file_path, 'BMP')
                            print(f"不规范尺寸，已移至WRONGSIZE: {file}")
                except Exception as e:
                    print(f"处理文件 {file} 时出错: {str(e)}")
                    continue

    print(f"\n>>> 图片转换完成：{source_dir}")
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
    shape_counter = 1
    grain_counter = 1
    
    for file_path in files:
        base_name = os.path.basename(file_path)
        name_without_ext, ext = os.path.splitext(base_name)
        
        # 检查文件名是否包含 shape 或 grain（不区分大小写）
        name_lower = name_without_ext.lower()
        if 'shape' in name_lower:
            new_filename = f"{folder_name}_s{shape_counter}{ext}"
            shape_counter += 1
        elif 'grain' in name_lower:
            new_filename = f"{folder_name}_g{grain_counter}{ext}"
            grain_counter += 1
        else:
            # 保留原始文件名，但确保不重复
            new_filename = ensure_unique_filename(name_without_ext, ext, existing_files)
        
        final_path = os.path.join(target_subdir, new_filename)
        try:
            shutil.copy2(file_path, final_path)
            existing_files.add(final_path)
            print(f"已复制: {base_name} -> {new_filename}")
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
    Parse archived textures of Procreate brushes, extracting .png/.jpg & .archive files.
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
        解压并提取 .png/.jpg & .archive 文件到 cache/<文件名>.brushset
        并把提取到的图片复制到 ./texture_shape
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

                # 检查是否为PNG或JPG文件
                if member.lower().endswith(('.png', '.jpg', '.jpeg')):
                    out_path = os.path.join(base_directory, member)
                    with archive.open(member) as f:
                        img = Image.open(f)
                        img.save(out_path)
                        print(f"已提取图片: {member}")
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

        # 将图片文件复制到 ./texture_shape/<brushsetName>.brushset/
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


def should_invert_image(img):
    """
    通过分析图像四边5像素宽度区域的像素来判断是否需要反转。
    如果四边的白色像素（亮度>200）占比超过60%，则认为是白底图片。
    返回 True 如果是白底黑图（需要反转），False 如果是黑底白图（不需要反转）。
    """
    # 转换为灰度图像
    if img.mode != 'L':
        img = img.convert('L')
    
    width, height = img.size
    pixels = img.load()
    edge_width = 5  # 检测边缘的宽度
    
    # 收集四边的像素
    edge_pixels = []
    
    # 上边 5 像素
    for y in range(edge_width):
        edge_pixels.extend([pixels[x, y] for x in range(width)])
    
    # 下边 5 像素
    for y in range(height - edge_width, height):
        edge_pixels.extend([pixels[x, y] for x in range(width)])
    
    # 左边 5 像素（不包括已经计算的角落）
    for x in range(edge_width):
        edge_pixels.extend([pixels[x, y] for y in range(edge_width, height - edge_width)])
    
    # 右边 5 像素（不包括已经计算的角落）
    for x in range(width - edge_width, width):
        edge_pixels.extend([pixels[x, y] for y in range(edge_width, height - edge_width)])
    
    # 计算白色像素（亮度>200）的比例
    white_pixels = sum(1 for p in edge_pixels if p > 200)
    white_ratio = white_pixels / len(edge_pixels)
    
    # 如果白色像素占比超过60%，认为是白底图片
    is_white_background = white_ratio > 0.6
    print(f"白色像素占比: {white_ratio:.2%}")
    
    return is_white_background

def invert_selected_image_files(auto_detect=False):
    """
    允许用户多选图像文件，对每一个执行反相处理，
    结果保存到同目录下的 invert 或 auto_invert 子文件夹，保持原文件名和格式
    """
    image_paths = filedialog.askopenfilenames(
        filetypes=[
            ("Image Files", "*.bmp;*.jpg;*.jpeg;*.png;*.tif;*.tiff"),
            ("BMP Files", "*.bmp"),
            ("JPEG Files", "*.jpg;*.jpeg"),
            ("PNG Files", "*.png"),
            ("TIFF Files", "*.tif;*.tiff"),
            ("All Files", "*.*")
        ],
        title="选择需要反相的图像文件"
    )
    if not image_paths:
        return

    for image_file in image_paths:
        src_dir = os.path.dirname(image_file)
        # 根据是否为自动检测模式选择不同的输出目录
        output_dir = "auto_invert" if auto_detect else "invert"
        target_dir = os.path.join(src_dir, output_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        filename = os.path.basename(image_file)
        out_path = os.path.join(target_dir, filename)

        try:
            with Image.open(image_file) as img:
                # 转换为RGB或L模式进行处理
                if img.mode in ['RGBA', 'LA']:
                    # 保持alpha通道不变
                    r, g, b, a = img.split()
                    rgb_img = Image.merge('RGB', (r, g, b))
                    if auto_detect:
                        needs_invert = should_invert_image(rgb_img)
                        if needs_invert:
                            rgb_inverted = rgb_img.point(lambda p: 255 - p)
                        else:
                            rgb_inverted = rgb_img
                    else:
                        rgb_inverted = rgb_img.point(lambda p: 255 - p)
                    # 重新合并alpha通道
                    inverted_image = Image.merge('RGBA', (*rgb_inverted.split(), a))
                else:
                    # 对于其他格式的图片直接处理
                    if auto_detect:
                        needs_invert = should_invert_image(img)
                        if needs_invert:
                            inverted_image = img.point(lambda p: 255 - p)
                        else:
                            inverted_image = img.copy()
                    else:
                        inverted_image = img.point(lambda p: 255 - p)

                # 保存时保持原始格式
                inverted_image.save(out_path, quality=95)
                print(f"已处理并保存：{out_path}")

        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")
            continue

    success_msg = "所选图像文件处理完成，并存储到各自文件夹的 "
    success_msg += "auto_invert/" if auto_detect else "invert/"
    success_msg += " 子目录。"
    messagebox.showinfo("完成", success_msg)


def update_progress(progress, label, progress_bar):
    progress_bar["value"] = progress
    label.config(text=f"进度: {int(progress)}%")
    label.update()

def reset_progress(label, progress_bar):
    progress_bar["value"] = 0
    label.config(text="进度: 0%")

def auto_detect_and_invert_bmp_files():
    """
    自动检测白底黑图并反转。
    支持的格式：PNG, JPG, JPEG, TIFF, BMP, GIF, WebP, PSD, ICO
    只对检测为白底的图片进行反转处理。
    """
    image_paths = filedialog.askopenfilenames(
        filetypes=[
            ("Image Files", "*.bmp;*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.gif;*.webp;*.psd;*.ico"),
            ("BMP Files", "*.bmp"),
            ("JPEG Files", "*.jpg;*.jpeg"),
            ("PNG Files", "*.png"),
            ("TIFF Files", "*.tif;*.tiff"),
            ("GIF Files", "*.gif"),
            ("WebP Files", "*.webp"),
            ("PSD Files", "*.psd"),
            ("ICO Files", "*.ico"),
            ("All Files", "*.*")
        ],
        title="选择需要自动检测并反相的图像文件"
    )
    if not image_paths:
        return

    for image_file in image_paths:
        src_dir = os.path.dirname(image_file)
        invert_dir = os.path.join(src_dir, "invert")
        if not os.path.exists(invert_dir):
            os.makedirs(invert_dir)

        filename = os.path.basename(image_file)
        out_path = os.path.join(invert_dir, filename)

        try:
            with Image.open(image_file) as img:
                # 如果是动图，只取第一帧
                if hasattr(img, 'is_animated') and img.is_animated:
                    img.seek(0)
                
                # 处理带透明通道的图片
                if img.mode in ['RGBA', 'LA']:
                    r, g, b, a = img.split()
                    rgb_img = Image.merge('RGB', (r, g, b))
                    if should_invert_image(rgb_img):
                        rgb_inverted = rgb_img.point(lambda p: 255 - p)
                        inverted_image = Image.merge('RGBA', (*rgb_inverted.split(), a))
                    else:
                        inverted_image = img.copy()
                else:
                    # 对于其他格式的图片直接处理
                    if should_invert_image(img):
                        inverted_image = img.point(lambda p: 255 - p)
                        print(f"检测到白底黑图，已反相：{filename}")
                    else:
                        inverted_image = img.copy()
                        print(f"检测到黑底白图，保持原样：{filename}")

                # 保存时保持原始格式
                inverted_image.save(out_path, quality=95)
                print(f"已保存到：{out_path}")

        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")
            continue

    messagebox.showinfo("完成", "自动检测并反转完成，结果保存在各自文件夹的 invert/ 子目录。")

def open_current_directory():
    """
    打开程序所在的文件夹
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe
        current_dir = os.path.dirname(sys.executable)
    else:
        # 如果是 Python 脚本
        current_dir = os.path.dirname(os.path.abspath(__file__))
    os.startfile(current_dir)

def show_readme():
    """
    显示 README 信息的窗口
    """
    readme_window = tk.Toplevel()
    readme_window.title("README")
    readme_window.geometry("600x500")
    readme_window.configure(bg="#2b2b2b")

    text_widget = tk.Text(
        readme_window,
        wrap=tk.WORD,
        bg="#2b2b2b",
        fg="white",
        font=("Helvetica", 11),
        padx=20,
        pady=20
    )
    text_widget.pack(expand=True, fill='both', padx=10, pady=10)

    readme_text = """###########
 
不能动的文件：
1. defult（配置ini文件用）
2. Images（prct官方材质素材）
3. _internal (别删)

其余:
1. cache: 缓存文件，随意删除。
2. texture_shape: 笔刷形状文件。存储bmp、ini、png。

测试范例都来自于作者自愿公开共享的笔刷，喜欢请支持原作者。
为什么不是default，因为编程的时候打错字了...

增加功能：
1. 压缩不规范的正方形图片至sai2标准分辨率。
2. 支持所有图片格式的提取，并转换为bmp。

###########

笔刷文件位置:C:/Users/用户/Documents/SYSTEMAX Software Development/SAIv2/settings

· blotmap 画笔形状-洇染
· bristle 画笔形状-鬃毛（举例:平笔。普通的图片素材不能放进这里。）
· scatter 画笔形状-散布
· brshape 画笔形状-形状
· brushtex 画笔纹理
· papertex 纸张质感（用在图层效果里）

普通笔刷导入:
1. 把画笔形状和画笔纹理分别导入对应的文件夹
2. 打开sai2新建画笔调整参数

散布笔刷导入:
1. 把画笔形状导入scatter文件夹，画笔纹理导入brushtex文件夹
2. 在scatter文件夹随便找一个.ini文件复制并重命名为你画笔形状文件的名字（如果有同名.ini文件可以不做这步）

###########

你好，我是阿缅。
因为procreate的笔刷太丰富，而ps里手动转bmp文件又真的恶心，
就写了一个这样的软件。

这个软件并不全都来自我的功劳，在此要感谢tohsakrat在github开源的brush-converter。我在此基础上做了一些功能添加和封装处理，有喜欢画画的程序员，或者喜欢编程的画师的话，也请给这个repo点个star。

tohsakrat的github链接：https://github.com/tohsakrat/Brush-Converter
我自己的github？呃...缘分到了自然会看到的啦...

界面和功能都很简陋，之后看需求再看是否需要添加内容吧！
祝大家画画开心！

"""

    text_widget.insert('1.0', readme_text)
    text_widget.configure(state='disabled')

    readme_window.update_idletasks()
    width = readme_window.winfo_width()
    height = readme_window.winfo_height()
    x = (readme_window.winfo_screenwidth() // 2) - (width // 2)
    y = (readme_window.winfo_screenheight() // 2) - (height // 2)
    readme_window.geometry(f'{width}x{height}+{x}+{y}')

def compress_images(image_paths, target_size):
    """
    压缩选中的图片到指定尺寸
    参数:
        image_paths: 图片路径列表
        target_size: 目标尺寸 (256, 512, 或 1024)
    """
    if not image_paths:
        return
    
    for image_path in image_paths:
        try:
            # 获取源文件信息
            src_dir = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            base_name, ext = os.path.splitext(filename)
            
            # 创建输出目录
            output_dir = os.path.join(src_dir, f"compress_{target_size}")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 打开并处理图片
            with Image.open(image_path) as img:
                # 如果是动图，只取第一帧
                if hasattr(img, 'is_animated') and img.is_animated:
                    img.seek(0)
                
                # 获取原始尺寸
                original_size = img.size
                max_original_dimension = max(original_size)
                
                # 如果图片尺寸小于目标尺寸，跳过
                if max_original_dimension <= target_size:
                    print(f"跳过 {filename}: 原始尺寸 {original_size} 小于目标尺寸 {target_size}x{target_size}")
                    continue
                
                # 计算新尺寸，保持宽高比
                ratio = target_size / max_original_dimension
                new_width = int(original_size[0] * ratio)
                new_height = int(original_size[1] * ratio)
                
                # 压缩图片
                resized_img = img.resize((new_width, new_height), Resampling.LANCZOS)
                
                # 保存图片，保持原始格式
                output_path = os.path.join(output_dir, filename)
                resized_img.save(output_path, quality=95)
                print(f"已压缩: {filename} ({original_size} -> {new_width}x{new_height})")
                
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")
            continue
    
    messagebox.showinfo("完成", f"图片压缩完成！\n已保存到 compress_{target_size}/ 文件夹")

def show_compress_window():
    """
    显示压缩图片的弹窗界面
    """
    compress_window = tk.Toplevel()
    compress_window.title("压缩图片")
    compress_window.geometry("400x300")
    compress_window.configure(bg="#2b2b2b")
    
    # 使弹窗居中显示
    compress_window.update_idletasks()
    width = compress_window.winfo_width()
    height = compress_window.winfo_height()
    x = (compress_window.winfo_screenwidth() // 2) - (width // 2)
    y = (compress_window.winfo_screenheight() // 2) - (height // 2)
    compress_window.geometry(f'{width}x{height}+{x}+{y}')
    
    # 标题
    title_label = Label(
        compress_window,
        text="图片压缩工具",
        foreground="white",
        background="#2b2b2b",
        font=("Helvetica", 12, "bold")
    )
    title_label.pack(pady=15)
    
    # 尺寸选择框
    size_frame = Frame(compress_window, style="TFrame")
    size_frame.pack(pady=10)
    
    size_label = Label(
        size_frame,
        text="目标尺寸:",
        foreground="white",
        background="#2b2b2b"
    )
    size_label.pack(side='left', padx=5)
    
    size_var = tk.StringVar(value="1024")
    size_options = ["256", "512", "1024"]
    size_menu = tk.OptionMenu(size_frame, size_var, *size_options)
    size_menu.config(width=8)
    size_menu.pack(side='left', padx=5)
    
    # 压缩按钮
    compress_button = tk.Button(
        compress_window,
        text="选择并压缩图片",
        command=lambda: browse_and_compress_images(size_var),
        width=20,
        height=2,
        bg="#4a4a4a",
        fg="white",
        font=("Helvetica", 10)
    )
    compress_button.pack(pady=15)
    
    # 说明文字
    info_text = (
        "※ 支持所有常见图片格式\n"
        "※ 保持原始宽高比进行压缩\n"
        "※ 小于目标尺寸的图片将被跳过\n"
        "※ 压缩后的图片将保存在原目录的\n"
        "   compress_[size] 文件夹中"
    )
    
    info_label = Label(
        compress_window,
        text=info_text,
        foreground="white",
        background="#2b2b2b",
        justify="left",
        font=("Helvetica", 10)
    )
    info_label.pack(pady=15)

def browse_and_compress_images(size_var):
    """
    打开文件选择对话框并压缩选中的图片
    """
    target_size = int(size_var.get())
    image_paths = filedialog.askopenfilenames(
        filetypes=[
            ("Image Files", "*.bmp;*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.gif;*.webp;*.psd;*.ico"),
            ("BMP Files", "*.bmp"),
            ("JPEG Files", "*.jpg;*.jpeg"),
            ("PNG Files", "*.png"),
            ("TIFF Files", "*.tif;*.tiff"),
            ("GIF Files", "*.gif"),
            ("WebP Files", "*.webp"),
            ("PSD Files", "*.psd"),
            ("ICO Files", "*.ico"),
            ("All Files", "*.*")
        ],
        title="选择需要压缩的图片文件"
    )
    
    if image_paths:
        compress_images(image_paths, target_size)

def show_crop_window():
    """
    显示裁剪图片的弹窗界面
    """
    crop_window = tk.Toplevel()
    crop_window.title("裁剪图片")
    crop_window.geometry("800x600")
    crop_window.configure(bg="#2b2b2b")
    
    # 居中显示窗口
    crop_window.update_idletasks()
    width = crop_window.winfo_width()
    height = crop_window.winfo_height()
    x = (crop_window.winfo_screenwidth() // 2) - (width // 2)
    y = (crop_window.winfo_screenheight() // 2) - (height // 2)
    crop_window.geometry(f'{width}x{height}+{x}+{y}')
    
    # 存储选中的文件和示例图片
    selected_files = []
    current_preview = {"path": None, "size": None}
    
    # 左侧控制面板
    control_frame = Frame(crop_window)
    control_frame.pack(side='left', padx=10, pady=10, fill='y')
    
    # 尺寸选择框
    size_frame = Frame(control_frame)
    size_frame.pack(pady=10)
    
    size_var = tk.StringVar(value="自定义")
    size_options = ["256", "512", "1024", "自定义"]
    
    def update_crop_box(*args):
        if not current_preview["path"]:
            return
            
        try:
            if size_var.get() == "自定义":
                crop_size = int(custom_size_entry.get())
                if crop_size <= 0:
                    raise ValueError()
            else:
                crop_size = int(size_var.get())
            show_crop_preview(current_preview["path"], crop_size, preview_canvas)
        except ValueError:
            messagebox.showerror("错误", "请输入有效的裁剪尺寸")
    
    def on_size_change(*args):
        if size_var.get() == "自定义":
            custom_size_entry.config(state='normal')
        else:
            custom_size_entry.config(state='disabled')
        update_crop_box()
    
    size_label = Label(
        size_frame,
        text="裁剪尺寸:",
        foreground="white",
        background="#2b2b2b"
    )
    size_label.pack(side='top', pady=5)
    
    size_menu = tk.OptionMenu(size_frame, size_var, *size_options)
    size_menu.config(width=8)
    size_menu.pack(side='top', pady=5)
    
    # 自定义尺寸输入框
    custom_size_frame = Frame(control_frame)
    custom_size_frame.pack(pady=5)
    
    custom_size_label = Label(
        custom_size_frame,
        text="自定义边长:",
        foreground="white",
        background="#2b2b2b"
    )
    custom_size_label.pack(side='top', pady=2)
    
    custom_size_entry = tk.Entry(custom_size_frame, width=10)
    custom_size_entry.pack(side='top', pady=2)
    custom_size_entry.insert(0, "256")
    custom_size_entry.bind('<Return>', update_crop_box)
    custom_size_entry.bind('<FocusOut>', update_crop_box)
    
    size_var.trace('w', on_size_change)
    
    # 图片预览区域
    preview_frame = Frame(crop_window)
    preview_frame.pack(side='right', expand=True, fill='both', padx=10, pady=10)
    
    preview_canvas = tk.Canvas(
        preview_frame,
        bg='#1a1a1a',
        highlightthickness=0
    )
    preview_canvas.pack(expand=True, fill='both')
    
    def select_files():
        files = filedialog.askopenfilenames(
            filetypes=[
                ("Image Files", "*.bmp;*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.gif;*.webp;*.psd;*.ico"),
                ("All Files", "*.*")
            ],
            title="选择需要裁剪的图片文件"
        )
        if files:
            selected_files.clear()
            selected_files.extend(files)
            # 默认使用第一张图片作为示例
            if not current_preview["path"]:
                show_crop_preview(files[0], 
                                int(size_var.get()) if size_var.get() != "自定义" else int(custom_size_entry.get()),
                                preview_canvas)
                current_preview["path"] = files[0]
                with Image.open(files[0]) as img:
                    current_preview["size"] = img.size
    
    def select_preview():
        preview = filedialog.askopenfilename(
            filetypes=[
                ("Image Files", "*.bmp;*.jpg;*.jpeg;*.png;*.tif;*.tiff;*.gif;*.webp;*.psd;*.ico"),
                ("All Files", "*.*")
            ],
            title="选择示例图片"
        )
        if preview:
            if preview not in selected_files:
                selected_files.append(preview)
            show_crop_preview(preview,
                            int(size_var.get()) if size_var.get() != "自定义" else int(custom_size_entry.get()),
                            preview_canvas)
            current_preview["path"] = preview
            with Image.open(preview) as img:
                current_preview["size"] = img.size
    
    def start_crop():
        if not selected_files:
            messagebox.showerror("错误", "请先选择需要裁剪的图片")
            return
            
        if not current_preview["path"]:
            messagebox.showerror("错误", "请先选择示例图片")
            return
            
        # 修改这里：使用 preview_canvas 而不是 canvas
        crop_box = preview_canvas.coords("crop_box")
        if not crop_box:
            messagebox.showerror("错误", "请先设置裁剪区域")
            return
            
        # 分类图片
        same_size_images = []
        different_size_images = []
        
        for file_path in selected_files:
            with Image.open(file_path) as img:
                if img.size == current_preview["size"]:
                    same_size_images.append(file_path)
                else:
                    different_size_images.append(file_path)
        
        # 处理相同尺寸的图片
        process_crop(same_size_images, crop_box, 
                    int(size_var.get()) if size_var.get() != "自定义" else int(custom_size_entry.get()),
                    preview_canvas)
        
        # 如果有不同尺寸的图片，询问用户
        if different_size_images:
            if messagebox.askyesno("提示", 
                                 f"发现{len(different_size_images)}张图片尺寸与示例图片不同。\n是否也要裁剪这些图片？"):
                process_crop(different_size_images, crop_box,
                           int(size_var.get()) if size_var.get() != "自定义" else int(custom_size_entry.get()),
                           preview_canvas)
    
    # 按钮区域
    button_frame = Frame(control_frame)
    button_frame.pack(pady=10)
    
    select_files_btn = tk.Button(
        button_frame,
        text="选择图片",
        command=select_files,
        width=15,
        bg="#4a4a4a",
        fg="white"
    )
    select_files_btn.pack(pady=5)
    
    select_preview_btn = tk.Button(
        button_frame,
        text="选择示例图片",
        command=select_preview,
        width=15,
        bg="#4a4a4a",
        fg="white"
    )
    select_preview_btn.pack(pady=5)
    
    start_crop_btn = tk.Button(
        button_frame,
        text="开始裁剪",
        command=start_crop,
        width=15,
        bg="#4a4a4a",
        fg="white"
    )
    start_crop_btn.pack(pady=5)

def show_crop_preview(image_path, crop_size, canvas):
    """
    显示预览图片和可拖动的裁剪框
    """
    canvas.delete("all")
    
    with Image.open(image_path) as img:
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        # 计算缩放比例
        scale = min(canvas_width/img.width, canvas_height/img.height)
        preview_width = int(img.width * scale)
        preview_height = int(img.height * scale)
        
        preview_img = img.resize((preview_width, preview_height), Resampling.LANCZOS)
        preview_photo = PhotoImage(image=preview_img)
        canvas.image = preview_photo
        
        # 显示图片
        preview_x = canvas_width//2 - preview_width//2
        preview_y = canvas_height//2 - preview_height//2
        canvas.create_image(
            canvas_width//2,
            canvas_height//2,
            image=preview_photo,
            anchor='center',
            tags="preview"
        )
        
        # 创建实际尺寸的裁剪框
        crop_box_size = int(crop_size * scale)
        initial_x = preview_x
        initial_y = preview_y
        
        # 创建裁剪框和拖动区域
        drag_padding = 15
        canvas.create_rectangle(
            initial_x - drag_padding, 
            initial_y - drag_padding,
            initial_x + crop_box_size + drag_padding,
            initial_y + crop_box_size + drag_padding,
            fill='',
            outline='',
            tags="drag_area"
        )
        
        canvas.create_rectangle(
            initial_x, initial_y,
            initial_x + crop_box_size,
            initial_y + crop_box_size,
            outline='red',
            width=2,
            tags="crop_box"
        )
        
        # 拖动相关变量
        drag_data = {"x": 0, "y": 0, "dragging": False}
        
        def start_drag(event):
            # 记录起始位置
            drag_data["x"] = event.x
            drag_data["y"] = event.y
            drag_data["dragging"] = True
            
        def drag(event):
            if not drag_data["dragging"]:
                return
                
            # 计算移动距离
            dx = event.x - drag_data["x"]
            dy = event.y - drag_data["y"]
            
            # 获取当前裁剪框位置
            box_coords = canvas.coords("crop_box")
            new_x1 = box_coords[0] + dx
            new_y1 = box_coords[1] + dy
            new_x2 = box_coords[2] + dx
            new_y2 = box_coords[3] + dy
            
            # 计算预览图片的边界
            preview_x = canvas_width//2 - preview_width//2
            preview_y = canvas_height//2 - preview_height//2
            preview_right = preview_x + preview_width
            preview_bottom = preview_y + preview_height
            
            # 调整到有效范围内
            if new_x1 < preview_x:
                dx = preview_x - box_coords[0]
            elif new_x2 > preview_right:
                dx = preview_right - box_coords[2]
            
            if new_y1 < preview_y:
                dy = preview_y - box_coords[1]
            elif new_y2 > preview_bottom:
                dy = preview_bottom - box_coords[3]
            
            # 移动裁剪框和拖动区域
            if dx != 0 or dy != 0:
                canvas.move("crop_box", dx, dy)
                canvas.move("drag_area", dx, dy)
            
            # 更新起始位置
            drag_data["x"] = event.x
            drag_data["y"] = event.y
        
        def stop_drag(event):
            drag_data["dragging"] = False
        
        # 绑定拖动事件到拖动区域
        canvas.tag_bind("drag_area", '<Button-1>', start_drag)
        canvas.tag_bind("drag_area", '<B1-Motion>', drag)
        canvas.tag_bind("drag_area", '<ButtonRelease-1>', stop_drag)
        
        # 改变鼠标样式
        def on_enter(event):
            canvas.configure(cursor="hand2")  # 或者使用 "fleur" 获得十字光标
            
        def on_leave(event):
            canvas.configure(cursor="")
            
        canvas.tag_bind("drag_area", '<Enter>', on_enter)
        canvas.tag_bind("drag_area", '<Leave>', on_leave)

def process_crop(file_paths, crop_coords, crop_size, preview_canvas):
    """
    根据指定的裁剪区域处理所有图片
    """
    if not file_paths:
        return
        
    # 创建输出目录
    first_file_dir = os.path.dirname(file_paths[0])
    output_dir = os.path.join(first_file_dir, f'crop_{crop_size}')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 获取预览图片的信息
    with Image.open(file_paths[0]) as img:
        # 计算画布上的缩放比例
        canvas_width = preview_canvas.winfo_width()
        canvas_height = preview_canvas.winfo_height()
        scale = min(canvas_width/img.width, canvas_height/img.height)
        
        # 计算预览图片在画布上的偏移量
        preview_width = int(img.width * scale)
        preview_height = int(img.height * scale)
        offset_x = (canvas_width - preview_width) // 2
        offset_y = (canvas_height - preview_height) // 2
        
        # 将画布坐标转换为原始图片坐标
        relative_x = int((crop_coords[0] - offset_x) / scale)
        relative_y = int((crop_coords[1] - offset_y) / scale)
        
        # 使用指定尺寸创建裁剪框
        crop_box = (
            relative_x,
            relative_y,
            relative_x + crop_size,
            relative_y + crop_size
        )
    
    # 处理所有图片
    for file_path in file_paths:
        try:
            with Image.open(file_path) as img:
                # 如果是动图，只取第一帧
                if hasattr(img, 'is_animated') and img.is_animated:
                    img.seek(0)
                
                # 检查裁剪区域是否超出图片范围
                if (crop_box[2] > img.width or crop_box[3] > img.height):
                    print(f"跳过 {os.path.basename(file_path)}: 裁剪区域超出图片范围")
                    continue
                
                # 直接裁剪指定区域
                cropped = img.crop(crop_box)
                
                # 保存裁剪后的图片
                output_path = os.path.join(output_dir, os.path.basename(file_path))
                cropped.save(output_path, quality=95)
                print(f"已裁剪: {os.path.basename(file_path)}")
                
        except Exception as e:
            print(f"处理 {os.path.basename(file_path)} 时出错: {str(e)}")
            continue
    
    # 显示成功信息
    messagebox.showinfo("完成", f"图片裁剪完成！\n已保存到 crop_{crop_size}/ 文件夹")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Procreate 笔刷工具箱")
    root.geometry("600x720")  # 设置窗口大小
    root.configure(bg="#2b2b2b")

    frame = Frame(root, style="TFrame")
    frame.pack(expand=True, fill='both', padx=20, pady=20)  # 添加padding，使用fill='both'填充

    # 添加红色警告文字
    warning_label = Label(
        frame,
        text="※ 第一次使用请先点击下方【查看说明文档】",
        foreground="white",
        background="#2b2b2b",
        font=("Helvetica", 12, "bold")
    )
    warning_label.pack(pady=5)

    # 把说明文档按钮放在最前面，并设置更大的尺寸
    readme_button = tk.Button(
        frame,
        text="查看说明文档",
        command=show_readme,
        width=25,
        height=2,
        bg="#4a4a4a",  # 设置背景色
        fg="white",    # 设置文字颜色
        font=("Helvetica", 11, "bold")  # 设置字体
    )
    readme_button.pack(pady=10)

    info_label = Label(
        frame,
        text=("1) 解析笔刷文件：选择.brushset文件，提取PNG、JPG、JPEG到 cache/ 与 texture_shape/\n"
              "2) 图像转BMP和INI：多次选文件夹，将各种图片格式(PNG/JPG/TIFF等)转换为BMP并赋予.ini\n"
              "3) 手动反相处理：多选图像文件，对每张图片执行反相处理\n"
              "4) 智能反相处理：多选图像文件，自动检测白底图片并执行反相处理\n"
              "5) 打开程序目录：快速打开程序所在的文件夹\n\n"
              "※ 重要提示：SAI中的白底图像需要进行反相处理！请使用智能反相功能\n"
              "※ 图像转BMP+反相支持的格式为：PNG, JPG, JPEG, TIFF, BMP, GIF, WebP, PSD, ICO\n"
              " \n"
              "※ 禁止二次售卖，此软件永远免费发布。\n"
              ),
        foreground="white",
        background="#2b2b2b",
        font=("Helvetica", 12),
        justify="left"
    )
    info_label.pack(pady=10)

    progress_label = Label(
        frame,
        text="进度: 0%",
        foreground="white",
        background="#2b2b2b",
        font=("Helvetica", 10)
    )
    progress_label.pack(pady=5)

    progress_bar = Progressbar(frame, orient="horizontal", length=500, mode="determinate")
    progress_bar.pack(pady=10)

    # 创建左右两列的容器
    columns_frame = Frame(frame)
    columns_frame.pack(expand=True, fill='both', padx=10)

    # 左列容器
    left_column = Frame(columns_frame)
    left_column.pack(side='left', expand=True, fill='both', padx=10)

    # 右列容器
    right_column = Frame(columns_frame)
    right_column.pack(side='right', expand=True, fill='both', padx=10)

        # 添加小标题【笔刷转换】
    brush_label = Label(
        left_column,
        text="【笔刷转换】",
        foreground="white",
        background="#2b2b2b",
        font=("Helvetica", 11, "bold")
    )
    brush_label.pack(pady=10)
    # 将按钮放入左列
    parse_button = Button(left_column, text="解析笔刷文件", command=lambda: browse_brushset(progress_label, progress_bar))
    parse_button.pack(pady=8, fill='x')

    convert_button = Button(left_column, text="图像转BMP和INI", command=browse_folders_for_bmp_and_ini)
    convert_button.pack(pady=8, fill='x')

    invert_button = Button(left_column, text="手动反相处理", command=lambda: invert_selected_image_files(auto_detect=False))
    invert_button.pack(pady=8, fill='x')

    auto_invert_button = Button(left_column, text="智能反相处理", command=lambda: invert_selected_image_files(auto_detect=True))
    auto_invert_button.pack(pady=8, fill='x')

    open_dir_button = Button(left_column, text="打开程序目录", command=open_current_directory)
    open_dir_button.pack(pady=8, fill='x')

    # 添加压缩图片的标题
    compress_label = Label(
        right_column,
        text="【图像处理】",
        foreground="white",
        background="#2b2b2b",
        font=("Helvetica", 11, "bold")
    )
    compress_label.pack(pady=10)

    # 添加压缩按钮
    compress_button = Button(
        right_column,
        text="压缩图片",
        command=show_compress_window
    )
    compress_button.pack(pady=8, fill='x')

    # 添加裁剪按钮
    crop_button = Button(right_column, text="裁剪图片", command=show_crop_window)
    crop_button.pack(pady=8, fill='x')

    root.mainloop()
