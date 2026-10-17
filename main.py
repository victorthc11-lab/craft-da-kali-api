import shutil
import os
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import List

# Cria a pasta imagens automaticamente se não existir
os.makedirs("imagens", exist_ok=True)

# Cola aqui o link que preparaste no bloco de notas (já com a tua password)
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:LnfQYdCxasavCTan@db.cteeekeastevbdokdden.supabase.co:5432/postgres"

# Repara que tirámos o "connect_args", pois o Postgres não precisa disso
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ProdutoDB(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String, index=True)
    descricao = Column(String)
    preco = Column(Float)
    categoria = Column(String)
    imagem_url = Column(String)
    disponivel = Column(Boolean, default=True)


Base.metadata.create_all(bind=engine)


class ProdutoCreate(BaseModel):
    nome: str
    descricao: str
    preco: float
    categoria: str
    imagem_url: str
    disponivel: bool = True


class ProdutoResponse(ProdutoCreate):
    id: int

    class Config:
        from_attributes = True


app = FastAPI(title="API Craft da Kali")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/imagens", StaticFiles(directory="imagens"), name="imagens")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- ROTAS DE PRODUTOS ---

@app.get("/produtos", response_model=List[ProdutoResponse])
async def listar_produtos(db: Session = Depends(get_db)):
    return db.query(ProdutoDB).all()


@app.post("/produtos", response_model=ProdutoResponse)
async def adicionar_produto(produto: ProdutoCreate, db: Session = Depends(get_db)):
    novo_produto = ProdutoDB(**produto.model_dump())
    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)
    return novo_produto


@app.delete("/produtos/{produto_id}")
async def deletar_produto(produto_id: int, db: Session = Depends(get_db)):
    produto = db.query(ProdutoDB).filter(ProdutoDB.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    db.delete(produto)
    db.commit()
    return {"mensagem": "Apagado com sucesso"}


# NOVO: Rota para Editar (Atualizar) um produto
@app.put("/produtos/{produto_id}", response_model=ProdutoResponse)
async def atualizar_produto(produto_id: int, produto_atualizado: ProdutoCreate, db: Session = Depends(get_db)):
    produto = db.query(ProdutoDB).filter(ProdutoDB.id == produto_id).first()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    produto.nome = produto_atualizado.nome
    produto.descricao = produto_atualizado.descricao
    produto.preco = produto_atualizado.preco
    produto.categoria = produto_atualizado.categoria
    produto.imagem_url = produto_atualizado.imagem_url

    db.commit()
    db.refresh(produto)
    return produto


# NOVO: Rota para fazer Upload da Imagem arrastada
@app.post("/upload-imagem/")
async def upload_imagem(file: UploadFile = File(...)):
    # Guarda o ficheiro fisicamente na pasta 'imagens'
    file_location = f"imagens/{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    # Devolve a URL automática para o front-end usar
    return {"imagem_url": f"http://127.0.0.1:8000/imagens/{file.filename}"}