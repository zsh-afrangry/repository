from sqlalchemy import select, delete as sa_delete
from sqlalchemy.orm import Session, selectinload

from app.models.bill import Tag, TagType
from app.schemas.tag import TagCreate, TagUpdate


def create_tag(db: Session, data: TagCreate) -> Tag:
    tag = Tag(**data.model_dump())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def get_tag(db: Session, tag_id: int) -> Tag | None:
    return db.get(Tag, tag_id)


def list_tags(db: Session, tag_type: TagType | None = None) -> list[Tag]:
    q = select(Tag).options(selectinload(Tag.children))
    if tag_type:
        q = q.where(Tag.type == tag_type)
    q = q.order_by(Tag.type, Tag.sort_order, Tag.name)
    return list(db.scalars(q).all())


def list_root_tags(db: Session, tag_type: TagType | None = None) -> list[Tag]:
    """Only top-level tags (no parent), with children loaded."""
    q = (
        select(Tag)
        .options(selectinload(Tag.children))
        .where(Tag.parent_id.is_(None))
    )
    if tag_type:
        q = q.where(Tag.type == tag_type)
    q = q.order_by(Tag.sort_order, Tag.name)
    return list(db.scalars(q).all())


def update_tag(db: Session, tag: Tag, data: TagUpdate) -> Tag:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)
    db.commit()
    db.refresh(tag)
    return tag


def delete_tag(db: Session, tag: Tag) -> None:
    db.delete(tag)
    db.commit()


def reseed_categories(db: Session) -> None:
    """Delete all category/subcategory tags and re-insert the canonical set.
    Payment platform / channel / fund_type tags are left untouched.
    Bills referencing deleted tags will have their FK set to NULL (ON DELETE SET NULL).
    """
    # Delete subcategories first (they reference categories via parent_id)
    db.execute(sa_delete(Tag).where(Tag.type == TagType.subcategory))
    db.execute(sa_delete(Tag).where(Tag.type == TagType.category))
    db.flush()

    categories: list[dict] = [
        {"name": "餐饮",  "sort_order": 1},
        {"name": "娱乐",  "sort_order": 2},
        {"name": "旅行",  "sort_order": 3},
        {"name": "日常",  "sort_order": 4},
        {"name": "工资",  "sort_order": 5},
        {"name": "奖金",  "sort_order": 6},
        {"name": "退款",  "sort_order": 7},
        {"name": "生活费","sort_order": 8},
    ]

    cat_objs: dict[str, Tag] = {}
    for d in categories:
        t = Tag(name=d["name"], type=TagType.category, sort_order=d["sort_order"])
        db.add(t)
        cat_objs[d["name"]] = t
    db.flush()  # populate ids before building children

    subcategories: list[tuple[str, list[tuple[str, int]]]] = [
        ("餐饮", [("早饭", 1), ("午饭", 2), ("晚饭", 3), ("夜宵", 4), ("饮料", 5), ("零食", 6)]),
        ("娱乐", [("购物", 1), ("虚拟会员", 2)]),
        ("旅行", [("住宿", 1), ("出行", 2), ("门票", 3)]),
        ("日常", [("交通", 1), ("工作", 2), ("医疗", 3)]),
    ]
    for cat_name, subs in subcategories:
        parent = cat_objs[cat_name]
        for sub_name, order in subs:
            db.add(Tag(name=sub_name, type=TagType.subcategory, parent_id=parent.id, sort_order=order))

    db.commit()


def seed_default_tags(db: Session) -> None:
    """Insert all default tags on first run (empty table)."""
    if db.scalar(select(Tag).limit(1)):
        return  # already seeded

    reseed_categories(db)

    # payment platforms
    for i, name in enumerate(["微信小程序", "抖音", "美团", "京东", "线下", "花呗", "淘宝", "拼多多"]):
        db.add(Tag(name=name, type=TagType.payment_platform, sort_order=i))

    # payment channels
    for i, name in enumerate(["微信", "支付宝", "银行卡"]):
        db.add(Tag(name=name, type=TagType.payment_channel, sort_order=i))

    # fund types
    for i, name in enumerate(["微信余额", "零钱通", "银行卡余额", "支付宝余额"]):
        db.add(Tag(name=name, type=TagType.fund_type, sort_order=i))

    db.commit()
