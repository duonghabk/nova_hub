# core/file_utils.py
import glob
from pathlib import Path
import subprocess
import shutil
import rarfile
import patoolib
import logging
import sys,os
from .logger_config import logger  

def delete_file_if_exists(path: str | Path) -> None:
    """Deletes a file if it exists, avoiding errors if it doesn't."""
    p = Path(path)
    if p.is_file():
        try:
            p.unlink()
            logger.info("Deleted file: %s", p)
        except Exception as e:
            logger.warning("Cannot delete file %s: %s", p, e)

def delete_dir_if_exists(path_pattern: str) -> None:
    """Deletes directories matching a pattern (supports wildcards)."""
    logger.debug("Attempting to delete directories matching: %s", path_pattern)
    for path in glob.glob(path_pattern):
        p = Path(path)
        if p.is_dir():
            try:
                shutil.rmtree(p)
                logger.info("Deleted directory: %s", p)
            except Exception as e:
                logger.warning("Cannot delete folder %s: %s", p, e)
        else:
            logger.debug("'%s' is not a directory, skipping.", p)

def extract_rar(rar_path: str | Path, extract_to: str | Path, password: str = "tungtools") -> None:
    """
    Extracts a .rar file, handling passwords efficiently by checking metadata first.
    """
    # rar_path = Path(rar_path)
    # extract_to = Path(extract_to)
    # extract_to.mkdir(parents=True, exist_ok=True)
    if not os.path.isfile(rar_path):
        print(f"Lỗi: File không tồn tại: {rar_path}")
        return False
    
    Path(extract_to).mkdir(parents=True, exist_ok=True)
    logger.info("Extracting '%s' to '%s'", rar_path, extract_to)
    try:
        patoolib.extract_archive(
            archive=str(Path(rar_path)),          # File RAR
            outdir=str(Path(extract_to)),     # Thư mục đích
            password=password,         # Mật khẩu (nếu có)
            interactive=False,         # Không hỏi input (tốt cho background)
            verbosity=0                # 0: bình thường, -1: silent, 1: verbose
        )
        logger.info("Successfully extracted '%s'", rar_path)
    except rarfile.BadRarFile as e:
        logger.error(f"Lỗi: File RAR không hợp lệ hoặc sai password: {e}")
        raise
    except rarfile.RarCannotExec as e:
        logger.error(f"Lỗi: Thiếu unrar binary hoặc không thể thực thi: {e}")
        raise
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {e}")
        raise


def run_exe(exe_path: str | Path) -> None:
    """
    Runs an .exe file (installer or application), setting the working
    directory to the file's location to ensure it can find its resources.
    """
    try:
        p_exe_path = Path(exe_path).resolve()
        exe_dir = p_exe_path.parent
        logger.info("Executing '%s' in working directory: %s", p_exe_path, exe_dir)
        subprocess.Popen([str(p_exe_path)], cwd=exe_dir)
    except Exception as e:
        logger.error("Error executing %s: %s", p_exe_path, e)
