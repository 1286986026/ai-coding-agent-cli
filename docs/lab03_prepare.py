from pathlib import Path


def main() -> None:
    """准备 Lab03 使用的独立教学目录和示例文件。"""

    # 项目根目录
    project_root = Path(__file__).resolve().parent.parent

    # Lab03 专用教学目录
    demo_dir = project_root / "demo_lab03"

    # 创建目录；如果已经存在则不报错
    demo_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 示例说明文件
    notes_file = demo_dir / "notes.txt"

    # 只在文件不存在时创建，避免覆盖已有内容
    if not notes_file.exists():
        notes_file.write_text(
            "Lab03 用于学习 GLMClient 与 ReAct Agent。\n"
            "工具的真实执行结果必须作为 Observation 回灌给模型。\n",
            encoding="utf-8",
        )

    # 按实验要求输出准备提示
    print("notes.txt ready")

    # 显示 notes.txt 中的两行说明
    print(notes_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()