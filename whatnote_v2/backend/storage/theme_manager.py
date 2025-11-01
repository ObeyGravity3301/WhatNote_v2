import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import UploadFile


class ThemeManager:
    """负责个性化主题与壁纸的文件管理与配置持久化"""

    DEFAULT_THEME = "win98"
    DEFAULT_LANGUAGE = "zh-CN"
    DEFAULT_WALLPAPER_BASENAME = "default_wallpaper"
    DEFAULT_DISPLAY_MODE = "fit"

    DISPLAY_MODES = [
        {"id": "fit", "label": "适应"},
        {"id": "stretch", "label": "拉伸"},
        {"id": "tile", "label": "平铺"},
        {"id": "cover", "label": "裁剪填充"},
        {"id": "none", "label": "无缩放"},
    ]

    AVAILABLE_THEMES = [
        {"id": "win98", "label": "Windows 98"}
    ]

    AVAILABLE_LANGUAGES = [
        {"code": "zh-CN", "label": "简体中文"}
    ]

    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

    def __init__(self) -> None:
        # backend/storage -> whatnote_v2 -> whatnote
        self.project_root = Path(__file__).resolve().parents[2]
        self.themes_dir = self.project_root / "themes"
        self.wallpapers_dir = self.themes_dir / "wallpapers"
        self.boards_wallpapers_dir = self.wallpapers_dir / "boards"
        self.config_path = self.themes_dir / "personalization.json"

        self._ensure_directories()
        self._ensure_config()
        self._migrate_board_wallpapers()

    # ------------------------------------------------------------------
    # 初始化与配置文件管理
    # ------------------------------------------------------------------
    def _ensure_directories(self) -> None:
        self.themes_dir.mkdir(parents=True, exist_ok=True)
        self.wallpapers_dir.mkdir(parents=True, exist_ok=True)
        self.boards_wallpapers_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_config(self) -> None:
        if not self.config_path.exists():
            config = {
                "theme": self.DEFAULT_THEME,
                "language": self.DEFAULT_LANGUAGE,
                "default_wallpaper": None,
                "boards": {},
                "board_wallpapers": [],
                "default_display_mode": self.DEFAULT_DISPLAY_MODE,
            }
            self._save_config(config)
            return

        config = self._load_config()
        changed = False

        if "default_display_mode" not in config:
            config["default_display_mode"] = self.DEFAULT_DISPLAY_MODE
            changed = True

        if "board_wallpapers" not in config or not isinstance(config.get("board_wallpapers"), list):
            config["board_wallpapers"] = []
            changed = True

        if "boards" not in config or not isinstance(config.get("boards"), dict):
            config["boards"] = {}
            changed = True

        if changed:
            self._save_config(config)

    def _migrate_board_wallpapers(self) -> None:
        """迁移旧版本中存储在各展板下的壁纸清单到全局列表"""
        if not self.config_path.exists():
            return

        config = self._load_config()
        boards = config.get("boards", {})
        global_list: List[Dict] = config.setdefault("board_wallpapers", [])
        existing_ids = {item.get("id") for item in global_list if item.get("id")}
        changed = False

        for board_id, entry in boards.items():
            if isinstance(entry, dict) and "display_mode" not in entry:
                entry["display_mode"] = None
                changed = True

            wallpapers = entry.pop("wallpapers", []) if isinstance(entry, dict) else []
            if not wallpapers:
                continue

            for meta in wallpapers:
                if not isinstance(meta, dict):
                    continue

                wallpaper_id = meta.get("id")
                if not wallpaper_id:
                    base = int(datetime.now().timestamp() * 1000)
                    wallpaper_id = f"wallpaper-{base}"
                    while wallpaper_id in existing_ids:
                        base += 1
                        wallpaper_id = f"wallpaper-{base}"
                    meta["id"] = wallpaper_id

                if wallpaper_id in existing_ids:
                    continue

                meta.setdefault("uploaded_by_board", board_id)
                global_list.append(meta)
                existing_ids.add(wallpaper_id)
                changed = True

        if changed:
            self._save_config(config)

    def _load_config(self) -> Dict:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_config(self, config: Dict) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 基础工具方法
    # ------------------------------------------------------------------
    def _validate_image(self, upload: UploadFile) -> Path:
        if not upload.filename:
            raise ValueError("未提供文件名")

        suffix = Path(upload.filename).suffix.lower()
        if suffix not in self.ALLOWED_EXTENSIONS:
            raise ValueError("仅支持上传图片文件：jpg/jpeg/png/gif/bmp/webp")

        return suffix

    def _copy_upload(self, upload: UploadFile, destination: Path) -> None:
        upload.file.seek(0)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as out_file:
            shutil.copyfileobj(upload.file, out_file)

    def _build_wallpaper_response(
        self,
        meta: Optional[Dict],
        path: Optional[Path],
        *,
        is_default: bool = False,
        board_id: Optional[str] = None,
    ) -> Optional[Dict]:
        if not meta or not path or not path.exists():
            return None

        try:
            stat = path.stat()
            version = int(stat.st_mtime)
        except FileNotFoundError:
            return None

        if is_default:
            wallpaper_id = "default"
            url = f"/api/personalization/wallpapers/default/image?v={version}"
        else:
            wallpaper_id = meta.get("id")
            if not wallpaper_id:
                return None
            url = f"/api/boards/{board_id}/wallpapers/{wallpaper_id}/image?v={version}"

        return {
            "id": wallpaper_id,
            "filename": meta.get("filename"),
            "originalName": meta.get("original_name"),
            "uploadedAt": meta.get("uploaded_at"),
            "url": url,
        }

    def _get_board_entry(self, config: Dict, board_id: str) -> Dict:
        boards = config.setdefault("boards", {})
        entry = boards.setdefault(board_id, {
            "selected_wallpaper_id": None,
            "display_mode": None,
        })

        # 清理旧字段
        if isinstance(entry, dict) and "wallpapers" in entry:
            entry.pop("wallpapers", None)
            self._save_config(config)

        if isinstance(entry, dict) and "display_mode" not in entry:
            entry["display_mode"] = None
            self._save_config(config)

        return entry

    def _resolve_wallpaper_path(self, meta: Dict) -> Path:
        filename = meta.get("filename")
        return self.wallpapers_dir / filename if filename else Path()

    # ------------------------------------------------------------------
    # 对外接口：获取设置
    # ------------------------------------------------------------------
    def get_settings(self, board_id: str) -> Dict:
        config = self._load_config()

        default_meta = config.get("default_wallpaper")
        default_path = (
            self._resolve_wallpaper_path(default_meta)
            if default_meta else None
        )
        default_wallpaper = self._build_wallpaper_response(
            default_meta, default_path, is_default=True
        )
        if default_wallpaper:
            default_wallpaper["displayMode"] = config.get("default_display_mode", self.DEFAULT_DISPLAY_MODE)

        board_entry = self._get_board_entry(config, board_id)

        wallpapers: List[Dict] = []
        cleaned_wallpapers: List[Dict] = []
        for meta in config.get("board_wallpapers", []):
            if not isinstance(meta, dict):
                continue

            path = self._resolve_wallpaper_path(meta)
            response = self._build_wallpaper_response(
                meta, path, board_id=board_id
            )
            if response:
                response["uploadedByBoard"] = meta.get("uploaded_by_board")
                wallpapers.append(response)
                cleaned_wallpapers.append(meta)

        # 如果有无效数据，写回清洗后的配置
        if len(cleaned_wallpapers) != len(config.get("board_wallpapers", [])):
            config["board_wallpapers"] = cleaned_wallpapers
            self._save_config(config)

        # 最新上传在前
        wallpapers.sort(key=lambda item: item.get("uploadedAt") or "", reverse=True)

        selected_id = board_entry.get("selected_wallpaper_id")
        applied = None

        if selected_id:
            selected_meta = next((m for m in cleaned_wallpapers if m.get("id") == selected_id), None)
            if selected_meta:
                selected_path = self._resolve_wallpaper_path(selected_meta)
                applied = self._build_wallpaper_response(
                    selected_meta, selected_path, board_id=board_id
                )
                if applied:
                    applied["type"] = "board"
                    applied["uploadedByBoard"] = selected_meta.get("uploaded_by_board")
                    applied["displayMode"] = board_entry.get("display_mode") or config.get("default_display_mode") or self.DEFAULT_DISPLAY_MODE
            else:
                # 选中的壁纸不存在，重置为默认
                board_entry["selected_wallpaper_id"] = None
                self._save_config(config)

        if not applied and default_wallpaper:
            applied = {**default_wallpaper, "type": "default"}
            applied["displayMode"] = board_entry.get("display_mode") or config.get("default_display_mode") or self.DEFAULT_DISPLAY_MODE

        return {
            "theme": config.get("theme", self.DEFAULT_THEME),
            "availableThemes": self.AVAILABLE_THEMES,
            "language": config.get("language", self.DEFAULT_LANGUAGE),
            "availableLanguages": self.AVAILABLE_LANGUAGES,
            "defaultWallpaper": default_wallpaper,
            "boardWallpapers": wallpapers,
            "selectedBoardWallpaperId": selected_id,
            "appliedWallpaper": applied,
            "boardDisplayMode": board_entry.get("display_mode") or config.get("default_display_mode") or self.DEFAULT_DISPLAY_MODE,
            "defaultDisplayMode": config.get("default_display_mode", self.DEFAULT_DISPLAY_MODE),
            "displayModes": self.DISPLAY_MODES,
        }

    # ------------------------------------------------------------------
    # 对外接口：默认壁纸
    # ------------------------------------------------------------------
    def save_default_wallpaper(self, upload: UploadFile) -> Dict:
        suffix = self._validate_image(upload)
        config = self._load_config()

        # 删除旧文件
        old_meta = config.get("default_wallpaper")
        if old_meta:
            old_path = self._resolve_wallpaper_path(old_meta)
            if old_path.exists():
                old_path.unlink()

        filename = f"{self.DEFAULT_WALLPAPER_BASENAME}{suffix}"
        destination = self.wallpapers_dir / filename
        self._copy_upload(upload, destination)

        meta = {
            "filename": filename,
            "original_name": upload.filename,
            "uploaded_at": datetime.now().isoformat(),
            "content_type": upload.content_type,
        }

        config["default_wallpaper"] = meta
        self._save_config(config)

        response = self._build_wallpaper_response(meta, destination, is_default=True)
        if response:
            response["displayMode"] = config.get("default_display_mode", self.DEFAULT_DISPLAY_MODE)
            response["type"] = "default"
        return response

    def get_default_wallpaper_path(self) -> Optional[Path]:
        config = self._load_config()
        meta = config.get("default_wallpaper")
        if not meta:
            return None
        path = self._resolve_wallpaper_path(meta)
        return path if path.exists() else None

    # ------------------------------------------------------------------
    # 对外接口：展板壁纸
    # ------------------------------------------------------------------
    def save_board_wallpaper(self, board_id: str, upload: UploadFile) -> Dict:
        suffix = self._validate_image(upload)
        config = self._load_config()
        board_entry = self._get_board_entry(config, board_id)

        existing_ids = {
            item.get("id")
            for item in config.get("board_wallpapers", [])
            if isinstance(item, dict) and item.get("id")
        }

        base = int(datetime.now().timestamp() * 1000)
        wallpaper_id = f"wallpaper-{base}"
        while wallpaper_id in existing_ids:
            base += 1
            wallpaper_id = f"wallpaper-{base}"
        rel_path = Path("boards") / board_id / f"{wallpaper_id}{suffix}"
        destination = self.wallpapers_dir / rel_path

        self._copy_upload(upload, destination)

        meta = {
            "id": wallpaper_id,
            "filename": str(rel_path).replace("\\", "/"),
            "original_name": upload.filename,
            "uploaded_at": datetime.now().isoformat(),
            "content_type": upload.content_type,
        }

        meta["uploaded_by_board"] = board_id

        board_wallpapers = config.setdefault("board_wallpapers", [])
        board_wallpapers.append(meta)

        self._save_config(config)

        response = self._build_wallpaper_response(meta, destination, board_id=board_id)
        if response:
            response["type"] = "board"
            response["uploadedByBoard"] = board_id
            response["displayMode"] = board_entry.get("display_mode") or config.get("default_display_mode") or self.DEFAULT_DISPLAY_MODE
        return response

    def get_board_wallpaper_path(self, board_id: str, wallpaper_id: str) -> Optional[Path]:
        config = self._load_config()

        meta = next(
            (item for item in config.get("board_wallpapers", []) if item.get("id") == wallpaper_id),
            None,
        )
        if not meta:
            return None

        path = self._resolve_wallpaper_path(meta)
        return path if path.exists() else None

    def select_board_wallpaper(self, board_id: str, wallpaper_id: Optional[str], display_mode: Optional[str] = None) -> Dict:
        config = self._load_config()
        board_entry = self._get_board_entry(config, board_id)

        if wallpaper_id:
            meta = next(
                (item for item in config.get("board_wallpapers", []) if item.get("id") == wallpaper_id),
                None,
            )
            if not meta:
                raise ValueError("指定的壁纸不存在")
            board_entry["selected_wallpaper_id"] = wallpaper_id
        else:
            board_entry["selected_wallpaper_id"] = None

        if display_mode is not None:
            board_entry["display_mode"] = self._validate_display_mode(display_mode)

        self._save_config(config)
        return self.get_settings(board_id)

    def set_default_display_mode(self, display_mode: str) -> str:
        config = self._load_config()
        config["default_display_mode"] = self._validate_display_mode(display_mode) or self.DEFAULT_DISPLAY_MODE
        self._save_config(config)
        return config["default_display_mode"]

    def _validate_display_mode(self, mode: Optional[str]) -> Optional[str]:
        if not mode:
            return None
        mode = mode.strip()
        valid_ids = {item["id"] for item in self.DISPLAY_MODES}
        if mode not in valid_ids:
            raise ValueError("不支持的壁纸显示模式")
        return mode


