"""圖片檔案與 Image 資料列一起管理：檔案放在 Config.IMG_PATH，資料列只存路徑。

檔案跟著 DB 交易走：新寫的檔案在交易沒 commit（rollback、close）時刪掉，
要刪的檔案等 commit 成功才真的刪，不會出現資料列還在、檔案卻不見的情況。
"""
import os
import shutil
import uuid

from flask import current_app
from sqlalchemy import event
from sqlalchemy.orm import Session

from models.image import Image
from models.shared import db


def save(data):
    """把圖片 bytes 存成新檔案與 Image 資料列，回傳 image id。"""
    image = _new_image()
    with open(image.path, "wb") as image_file:
        image_file.write(data)
    return image.id


def copy(image_id):
    """複製一張圖片成新的檔案與資料列；來源不存在時回傳 None。"""
    source = path(image_id)
    if not source:
        current_app.logger.warning(f"Image to copy not found: {image_id}")
        return None
    image = _new_image()
    shutil.copy2(source, image.path)
    return image.id


def delete(image_id):
    """刪除 Image 資料列，檔案在 commit 後才刪；資料列不存在時不做事。"""
    image = db.session.get(Image, image_id)
    if image:
        db.session.delete(image)
        _pending(db.session)["gone"].append(image.path)


def path(image_id):
    """圖片檔案的路徑；資料列或檔案不存在時回傳 None。"""
    image = db.session.get(Image, image_id) if image_id else None
    if image and os.path.exists(image.path):
        return image.path
    return None


def _new_image():
    image_dir = current_app.config["IMG_PATH"]
    os.makedirs(image_dir, exist_ok=True)
    name = uuid.uuid4().hex
    image = Image(name=name, path=os.path.join(image_dir, f"{name}.png"))
    db.session.add(image)
    db.session.flush()
    _pending(db.session)["new"].append(image.path)
    return image


def _pending(session):
    return session.info.setdefault("image_store", {"new": [], "gone": []})


def _remove(paths):
    for file_path in paths:
        if os.path.exists(file_path):
            os.remove(file_path)


@event.listens_for(Session, "after_commit")
def _after_commit(session):
    pending = session.info.pop("image_store", None)
    if pending:
        _remove(pending["gone"])


@event.listens_for(Session, "after_transaction_end")
def _after_transaction_end(session, transaction):
    # commit 時 after_commit 已經清掉；還留著表示交易沒有 commit
    if transaction.parent is None:
        pending = session.info.pop("image_store", None)
        if pending:
            _remove(pending["new"])
