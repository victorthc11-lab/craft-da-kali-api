import os
import time
import shutil # <-- Adicionado para lidar com ficheiros físicos
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import List
from supabase import create_client, Client

# --- CONFIGURAÇÕES DO SUPABASE STORAGE ---
SUPABASE_URL = "https://cteeekeastevbdokdden.supabase.co"
SUPABASE_KEY = "sb_secret_WTLUQvbjjxrec-L6wU3bJg_W3H6XQcw"# <-- COLA AQUI A TUA CHAVE SECRETA DE NOVO

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

os.makedirs("imagens", exist_ok=True)

SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres.cteeekeastevbdokdden:LnfQYdCxasavCTan@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

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

@app.post("/upload-imagem/")
async def upload_imagem(file: UploadFile = File(...)):
    nome_seguro = f"{int(time.time())}_{file.filename.replace(' ', '_')}"
    file_location = f"imagens/{nome_seguro}"

    # 1. Guarda a imagem fisicamente primeiro (Resolve bugs da biblioteca do Supabase)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    try:
        # 2. Faz upload do ficheiro físico para o Supabase
        supabase.storage.from_("produtos").upload(nome_seguro, file_location)

        # 3. Pede o link público permanente
        url_publica = supabase.storage.from_("produtos").get_public_url(nome_seguro)

        return {"imagem_url": url_publica}

    except Exception as e:
        # 4. Se falhar, vai "gritar" o erro exato no painel do Render!
        print(f"========== ERRO FATAL NO SUPABASE ==========")
        print(str(e))
        print(f"============================================")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
