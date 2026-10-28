import os
from contextlib import asynccontextmanager
from typing import Generator, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Float, Integer, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

# ---------- Database ----------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/products_db",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)  # tạo bảng nếu chưa có
    yield


app = FastAPI(
    title="Products API",
    version="1.0.0",
    description="CRUD products với PostgreSQL để test API tự động.",
    lifespan=lifespan,
)


# ---------- Schemas ----------
class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Laptop Dell XPS"])
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0, examples=[1500.0])
    stock: int = Field(0, ge=0, examples=[10])


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)


class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ---------- Endpoints ----------
@app.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@app.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED, tags=["products"])
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    product = ProductModel(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/products", response_model=List[Product], tags=["products"])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(ProductModel).order_by(ProductModel.id).offset(skip).limit(limit)
    return db.scalars(stmt).all()


@app.get("/products/{product_id}", response_model=Product, tags=["products"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(ProductModel, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.put("/products/{product_id}", response_model=Product, tags=["products"])
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(ProductModel, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        # cột NOT NULL không nhận null; chỉ description được phép set về null
        if value is None and key != "description":
            continue
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


# ---------- DELETE: đang comment để test chức năng update suite ----------
# Bỏ comment đoạn dưới rồi chạy lại để sinh ra thay đổi trong OpenAPI.
#
# @app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["products"])
# def delete_product(product_id: int, db: Session = Depends(get_db)):
#     product = db.get(ProductModel, product_id)
#     if not product:
#         raise HTTPException(status_code=404, detail="Product not found")
#     db.delete(product)
#     db.commit()
#     return None
