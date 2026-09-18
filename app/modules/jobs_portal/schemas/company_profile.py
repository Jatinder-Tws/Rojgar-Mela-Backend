from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
import re


def normalize_website(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    if not re.match(r"^https?://", raw, re.I):
        raw = f"https://{raw}"
    return raw[:500]


class CompanyReviewItem(BaseModel):
    author_name: Optional[str] = None
    rating: Optional[float] = None
    text: Optional[str] = None
    relative_time: Optional[str] = None


class CompanyGalleryImageOut(BaseModel):
    id: str
    image_url: str
    caption: Optional[str] = None
    sort_order: int = 0
    source: Optional[str] = None

    class Config:
        from_attributes = True


class CompanyPlaceCandidate(BaseModel):
    place_id: str
    name: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None


class CompanyLookupRequest(BaseModel):
    website: Optional[str] = None
    query: Optional[str] = None
    place_id: Optional[str] = None

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        return normalize_website(v)

    @field_validator("query", "place_id")
    @classmethod
    def strip_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class CompanyLookupPreview(BaseModel):
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    company_about: Optional[str] = None
    company_address: Optional[str] = None
    company_location: Optional[str] = None
    company_city: Optional[str] = None
    company_state: Optional[str] = None
    company_rating: Optional[float] = None
    company_review_count: Optional[int] = None
    company_reviews: List[CompanyReviewItem] = Field(default_factory=list)
    company_rating_source: Optional[str] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    logo_url: Optional[str] = None
    photo_references: List[str] = Field(default_factory=list)


class CompanyLookupResponse(BaseModel):
    places_enabled: bool
    source: str  # google | website | manual
    message: str
    preview: CompanyLookupPreview
    candidates: List[CompanyPlaceCandidate] = Field(default_factory=list)


class CompanyProfileUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    company_about: Optional[str] = None
    company_address: Optional[str] = None
    company_location: Optional[str] = None
    company_rating: Optional[float] = None
    company_review_count: Optional[int] = None
    company_reviews: Optional[List[CompanyReviewItem]] = None
    company_rating_source: Optional[str] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None

    @field_validator("company_website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        return normalize_website(v)

    @field_validator("company_about")
    @classmethod
    def validate_about(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v[:4000] if v else None

    @field_validator("company_rating")
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if v < 0 or v > 5:
            raise ValueError("Rating must be between 0 and 5")
        return round(float(v), 1)

    @field_validator("company_review_count")
    @classmethod
    def validate_review_count(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if v < 0:
            raise ValueError("Review count cannot be negative")
        return int(v)

    @field_validator("company_reviews")
    @classmethod
    def validate_reviews(cls, v: Optional[List[CompanyReviewItem]]) -> Optional[List[CompanyReviewItem]]:
        if v is None:
            return None
        return v[:8]


class CompanyApplyLookupRequest(BaseModel):
    website: Optional[str] = None
    query: Optional[str] = None
    place_id: Optional[str] = None
    import_photos: bool = True

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        return normalize_website(v)


class CompanyProfileOut(BaseModel):
    places_enabled: bool
    company_name: Optional[str] = None
    company_website: Optional[str] = None
    company_about: Optional[str] = None
    company_address: Optional[str] = None
    company_location: Optional[str] = None
    company_size: Optional[str] = None
    industry: Optional[str] = None
    company_rating: Optional[float] = None
    company_review_count: Optional[int] = None
    company_reviews: List[CompanyReviewItem] = Field(default_factory=list)
    company_rating_source: Optional[str] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    logo_url: Optional[str] = None
    gallery: List[CompanyGalleryImageOut] = Field(default_factory=list)
