"""SEO: блог, страницы (ТЗ часть 3)."""
import re
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from internal_admin.deps import require_seo
from internal_admin.models import SeoBlogPost, SeoBlogPostStatus, SeoSitePage
from internal_admin.schemas import SeoBlogPostCreate, SeoBlogPostUpdate, SeoSitePageUpdate

router = APIRouter(tags=["Internal SEO"])


def _slugify(value: str) -> str:
    s = value.strip().lower()
    s = re.sub(r"[^a-z0-9а-яё\\-]+", "-", s, flags=re.I)
    return re.sub(r"-+", "-", s).strip("-") or "post"


def _meta_issues(title: str | None, desc: str | None) -> list[str]:
    issues = []
    tl = len(title or "")
    dl = len(desc or "")
    if not title:
        issues.append("no_title")
    elif tl < 45:
        issues.append("short_title")
    elif tl > 65:
        issues.append("long_title")
    if not desc:
        issues.append("no_description")
    elif dl < 110:
        issues.append("short_description")
    elif dl > 165:
        issues.append("long_description")
    return issues


@router.get("/articles/summary")
@router.get("/blog/stats")
def blog_stats(staff=Depends(require_seo), db: Session = Depends(get_db)):
    published = db.query(func.count(SeoBlogPost.id)).filter(SeoBlogPost.status == SeoBlogPostStatus.PUBLISHED).scalar() or 0
    drafts = db.query(func.count(SeoBlogPost.id)).filter(SeoBlogPost.status == SeoBlogPostStatus.DRAFT).scalar() or 0
    traffic = db.query(func.coalesce(func.sum(SeoBlogPost.traffic_monthly), 0)).scalar() or 0
    missing_meta = 0
    for p in db.query(SeoBlogPost).all():
        if not p.meta_title or not p.meta_description:
            missing_meta += 1
    return {
        "published_count": int(published),
        "draft_count": int(drafts),
        "traffic_monthly": int(traffic),
        "missing_meta_count": missing_meta,
    }


@router.get("/articles")
@router.get("/blog/posts")
def list_blog_posts(
    q: str | None = None,
    status: str | None = None,
    staff=Depends(require_seo),
    db: Session = Depends(get_db),
):
    query = db.query(SeoBlogPost).order_by(SeoBlogPost.updated_at.desc())
    if status:
        try:
            query = query.filter(SeoBlogPost.status == SeoBlogPostStatus(status))
        except ValueError:
            pass
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.filter(func.lower(SeoBlogPost.title).like(like))
    rows = query.all()
    return {
        "items": [
            {
                "id": str(p.id),
                "slug": p.slug,
                "title": p.title,
                "status": p.status.value,
                "meta_title": p.meta_title,
                "meta_description": p.meta_description,
                "meta_issues": _meta_issues(p.meta_title, p.meta_description),
                "traffic_monthly": p.traffic_monthly,
                "category": p.category,
                "updated_at": p.updated_at,
            }
            for p in rows
        ]
    }


@router.post("/articles")
@router.post("/blog/posts")
def create_blog_post(body: SeoBlogPostCreate, staff=Depends(require_seo), db: Session = Depends(get_db)):
    slug = _slugify(body.slug or body.title)
    if db.query(SeoBlogPost).filter(SeoBlogPost.slug == slug).first():
        raise HTTPException(status_code=400, detail="Slug already exists")
    post = SeoBlogPost(
        slug=slug,
        title=body.title,
        content_html=body.content_html,
        category=body.category,
        meta_title=body.meta_title,
        meta_description=body.meta_description,
        keywords=body.keywords,
        cover_url=body.cover_url,
        traffic_monthly=body.traffic_monthly,
        author_user_id=staff.id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": str(post.id), "slug": post.slug}


@router.get("/articles/{post_id}")
@router.get("/blog/posts/{post_id}")
def get_blog_post(post_id: UUID, staff=Depends(require_seo), db: Session = Depends(get_db)):
    post = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return {
        "id": str(post.id),
        "slug": post.slug,
        "title": post.title,
        "content_html": post.content_html,
        "status": post.status.value,
        "category": post.category,
        "meta_title": post.meta_title,
        "meta_description": post.meta_description,
        "keywords": post.keywords,
        "cover_url": post.cover_url,
        "traffic_monthly": post.traffic_monthly,
        "seo_score": 72,
        "seo_issues": _meta_issues(post.meta_title, post.meta_description),
    }


@router.patch("/articles/{post_id}")
@router.patch("/blog/posts/{post_id}")
def update_blog_post(post_id: UUID, body: SeoBlogPostUpdate, staff=Depends(require_seo), db: Session = Depends(get_db)):
    post = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    data = body.model_dump(exclude_unset=True)
    if "status" in data:
        post.status = SeoBlogPostStatus(data["status"])
        data.pop("status")
    for k, v in data.items():
        setattr(post, k, v)
    db.commit()
    return {"ok": True}


@router.post("/upload/image")
async def upload_seo_image(
    file: UploadFile = File(...),
    staff=Depends(require_seo),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads allowed")
    upload_dir = Path(__file__).resolve().parents[2] / "static" / "seo_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "image.bin").suffix or ".bin"
    name = f"{uuid.uuid4().hex}{ext}"
    dest = upload_dir / name
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    dest.write_bytes(data)
    return {"url": f"/static/seo_uploads/{name}"}


@router.get("/pages")
def list_site_pages(staff=Depends(require_seo), db: Session = Depends(get_db)):
    rows = db.query(SeoSitePage).order_by(SeoSitePage.path).all()
    return {
        "items": [
            {
                "id": str(p.id),
                "path": p.path,
                "title": p.title,
                "meta_title": p.meta_title,
                "meta_description": p.meta_description,
                "meta_issues": _meta_issues(p.meta_title, p.meta_description),
                "traffic_monthly": p.traffic_monthly,
            }
            for p in rows
        ]
    }


@router.patch("/pages/{page_id}")
def update_site_page(page_id: UUID, body: SeoSitePageUpdate, staff=Depends(require_seo), db: Session = Depends(get_db)):
    page = db.query(SeoSitePage).filter(SeoSitePage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(page, k, v)
    page.updated_by = staff.id
    db.commit()
    return {"ok": True}


@router.post("/articles/{post_id}/publish")
def publish_article(post_id: UUID, staff=Depends(require_seo), db: Session = Depends(get_db)):
    post = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = SeoBlogPostStatus.PUBLISHED
    from datetime import datetime, timezone

    post.published_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": "published"}


@router.post("/articles/{post_id}/unpublish")
def unpublish_article(post_id: UUID, staff=Depends(require_seo), db: Session = Depends(get_db)):
    post = db.query(SeoBlogPost).filter(SeoBlogPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.status = SeoBlogPostStatus.DRAFT
    post.published_at = None
    db.commit()
    return {"ok": True, "status": "draft"}
