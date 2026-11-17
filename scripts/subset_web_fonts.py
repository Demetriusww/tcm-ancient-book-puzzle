"""Create small browser-only font subsets before the Pygbag build."""

from __future__ import annotations

import argparse
from pathlib import Path

from fontTools import subset


TEXT_SUFFIXES = {".json", ".md", ".py", ".txt"}
ASCII_AND_PUNCTUATION = (
    "".join(chr(code) for code in range(0x20, 0x7F))
    + "，。！？；：、“”‘’（）《》【】—…·「」『』〈〉～￥％＃＠＆＊"
    + "＋－／＝＿｜＼　"
)


def read_game_text(stage_dir: Path) -> str:
    parts: list[str] = []
    for path in stage_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            parts.append(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
    return "".join(parts)


def gb2312_level_one() -> set[str]:
    characters: set[str] = set()
    for high in range(0xB0, 0xD8):
        for low in range(0xA1, 0xFF):
            try:
                characters.add(bytes((high, low)).decode("gb2312"))
            except UnicodeDecodeError:
                continue
    return characters


def write_subset(source: Path, target: Path, characters: set[str]) -> None:
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.recalc_bounds = True
    options.recalc_timestamp = False

    font = subset.load_font(source, options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes={ord(character) for character in characters})
    subsetter.subset(font)
    target.parent.mkdir(parents=True, exist_ok=True)
    subset.save_font(font, target, options)
    font.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", type=Path, help="Pygbag staging directory")
    args = parser.parse_args()

    stage_dir = args.stage.resolve()
    fonts_dir = stage_dir / "assets" / "fonts"
    game_characters = set(read_game_text(stage_dir)) | set(ASCII_AND_PUNCTUATION)

    display_chars = game_characters
    body_chars = game_characters | gb2312_level_one()

    targets = (
        ("MaShanZheng-Regular.ttf", display_chars),
        ("ZCOOLXiaoWei-Regular.ttf", body_chars),
    )
    for filename, characters in targets:
        source = fonts_dir / filename
        if not source.exists():
            continue
        before = source.stat().st_size
        write_subset(source, source, characters)
        after = source.stat().st_size
        print(
            f"{filename}: {before:,} -> {after:,} bytes "
            f"({after / before:.1%})"
        )


if __name__ == "__main__":
    main()
