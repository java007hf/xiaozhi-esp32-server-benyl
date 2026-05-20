import os
import importlib.util
import asyncio
import ast
import site

print("使用前请根据 docs/performance_tester.md 的说明准备配置。")


def configure_windows_opus_dll_path():
    if os.name != "nt":
        return

    for site_packages_dir in site.getsitepackages() + [site.getusersitepackages()]:
        pyogg_dir = os.path.join(site_packages_dir, "pyogg")
        opus_dll = os.path.join(pyogg_dir, "opus.dll")
        if os.path.exists(opus_dll):
            os.environ["PATH"] = pyogg_dir + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(pyogg_dir)
            return


configure_windows_opus_dll_path()


def list_performance_tester_modules():
    performance_tester_dir = os.path.join(
        os.path.dirname(__file__), "performance_tester"
    )
    modules = []
    for file in os.listdir(performance_tester_dir):
        if file.endswith(".py"):
            modules.append(file[:-3])
    return modules


async def load_and_execute_module(module_name):
    module_path = os.path.join(
        os.path.dirname(__file__), "performance_tester", f"{module_name}.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "main"):
        main_func = module.main
        if asyncio.iscoroutinefunction(main_func):
            await main_func()
        else:
            main_func()
    else:
        print(f"模块 {module_name} 中没有找到 main 函数。")


def get_module_description(module_name):
    module_path = os.path.join(
        os.path.dirname(__file__), "performance_tester", f"{module_name}.py"
    )
    try:
        with open(module_path, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read(), filename=module_path)
    except (OSError, SyntaxError):
        return "暂无描述"

    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "description"
                for target in node.targets
            )
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    return "暂无描述"


def main():
    modules = list_performance_tester_modules()
    if not modules:
        print("performance_tester 目录中没有可用的性能测试工具。")
        return

    print("可用的性能测试工具：")
    for idx, module in enumerate(modules, 1):
        description = get_module_description(module)
        print(f"{idx}. {module} - {description}")

    try:
        choice = int(input("请选择要调用的性能测试工具编号：")) - 1
        if 0 <= choice < len(modules):
            try:
                asyncio.run(load_and_execute_module(modules[choice]))
            except ModuleNotFoundError as err:
                missing_module = err.name or str(err)
                print(
                    f"缺少依赖模块：{missing_module}。请先执行："
                    "pip install -r requirements.txt"
                )
            except FileNotFoundError as err:
                print(f"缺少配置文件：{err}")
                print("请按 docs/performance_tester.md 准备 data/.config.yaml。")
            except Exception as err:
                if "Could not find Opus library" in str(err):
                    print(
                        "缺少 Windows Opus 动态库。请先执行："
                        "pip install -r requirements.txt"
                    )
                else:
                    raise
        else:
            print("无效的选择。")
    except ValueError:
        print("请输入有效的数字。")


if __name__ == "__main__":
    main()
