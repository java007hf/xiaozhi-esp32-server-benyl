import os
import asyncio
from config.config_loader import read_config, get_project_dir, load_config


default_config_file = "config.yaml"
config_file_valid = False


def check_config_file():
    global config_file_valid
    if config_file_valid:
        return
    """
    简化的配置检查，仅提示用户配置文件的使用情况
    """
    custom_config_file = get_project_dir() + "data/." + default_config_file
    if not os.path.exists(custom_config_file):
        raise FileNotFoundError(
            "找不到data/.config.yaml文件，请按教程确认该配置文件是否存在"
        )

    # 检查是否从API读取配置
    config = asyncio.run(load_config())
    if config.get("read_config_from_api", False):
        print("从API读取配置")
        old_config_origin = read_config(custom_config_file)
        if old_config_origin.get("selected_module") is not None:
            print("[提示] 本地配置包含 selected_module，智控台配置将优先使用，本地配置作为默认回退")
    config_file_valid = True
