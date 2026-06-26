from __future__ import annotations
import os
import json
from pathlib import Path
from flask import Flask, render_template, request, session, jsonify
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect
from datetime import datetime, date
import re

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

# -------------------------------------------------------------
# Configuração do banco de dados com fallback automático
# -------------------------------------------------------------
def configurar_banco():
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        # Limpeza e formatação da URL
        url_limpa = database_url.strip().replace('(', '').replace(')', '').strip()
        
        # Substitui 'postgres://' por 'postgresql://' (SQLAlchemy exige)
        if url_limpa.startswith("postgres://"):
            url_limpa = url_limpa.replace("postgres://", "postgresql://", 1)
        
        # Se for URL do pooler do Supabase, ajusta para conexão direta (opcional)
        if 'pooler.supabase.com' in url_limpa:
            url_limpa = url_limpa.replace('pooler.supabase.com', 'supabase.co')
            # Remove prefixo AWS se existir
            url_limpa = re.sub(r'aws-\d+-[a-z]+-\d+\.', '', url_limpa)
            print("🔄 Usando conexão direta do Supabase (sem pooler)")

        # NÃO força driver psycopg2, deixa o SQLAlchemy detectar
        try:
            app.config["SQLALCHEMY_DATABASE_URI"] = url_limpa
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_recycle": 300,
                "pool_pre_ping": True,
            }
            # Testa a conexão com um engine temporário
            from sqlalchemy import create_engine
            engine = create_engine(url_limpa, **app.config["SQLALCHEMY_ENGINE_OPTIONS"])
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            print("✅ Conectado ao Supabase (PostgreSQL) com sucesso!")
            return "supabase"
        except Exception as e:
            print(f"❌ Falha na conexão com Supabase: {e}")
            print("🔄 Fallback para SQLite local...")

    # Fallback para SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
    print("✅ Usando SQLite local (fallback)")
    return "sqlite"

tipo_banco = configurar_banco()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)  # Apenas uma instância

# -------------------------------------------------------------
# Modelos
# -------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    nivel = db.Column(db.String(20), default="funcionario")

    def set_password(self, raw):
        self.password_hash = bcrypt.generate_password_hash(raw).decode()

    def check_password(self, raw):
        return bcrypt.check_password_hash(self.password_hash, raw)

class Cliente(db.Model):
    __tablename__ = "clientes"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    placa = db.Column(db.String(10), nullable=False, unique=True)
    veiculo = db.Column(db.String(50), default="Carro")
    plano = db.Column(db.String(20), default="Mensal")
    mensalidade = db.Column(db.Float, default=0.0)
    inicio = db.Column(db.Date, nullable=False)
    vencimento = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default="Pendente")
    observacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Produto(db.Model):
    __tablename__ = "produtos"
    id = db.Column(db.Integer, primary_key=True)
    produto = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), default="Limpeza")
    unidade = db.Column(db.String(20), default="Unidade")
    quantidade = db.Column(db.Float, default=0)
    estoque_min = db.Column(db.Float, default=0)
    preco = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Lavagem(db.Model):
    __tablename__ = "lavagens"
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'))
    cliente_nome = db.Column(db.String(100), nullable=False)
    placa = db.Column(db.String(10), nullable=False)
    servico = db.Column(db.String(50), nullable=False)
    funcionario = db.Column(db.String(50), nullable=False)
    tipo = db.Column(db.String(20), default="assinante")
    preco = db.Column(db.Float, default=0.0)
    observacoes = db.Column(db.Text)
    produtos_utilizados = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------------------------------------------------
# Funções auxiliares
# -------------------------------------------------------------
def logged_in():
    return bool(session.get("uid"))

def init_db():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tabelas criadas/verificadas")
            if not User.query.first():
                admin = User(username="admin", nivel="admin", is_admin=True)
                admin.set_password("1234")
                db.session.add(admin)
                db.session.commit()
                print("✅ Usuário admin criado: admin / 1234")
        except Exception as e:
            print(f"⚠️ Erro na inicialização: {e}")

# -------------------------------------------------------------
# Rotas da API (coloque aqui todas as suas rotas existentes)
# -------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        session["uid"] = user.id
        session["username"] = user.username
        session["nivel"] = user.nivel
        return jsonify({
            'success': True,
            'user': {
                'nome': user.username,
                'username': user.username,
                'nivel': user.nivel
            }
        })
    return jsonify({'success': False, 'message': 'Credenciais inválidas'}), 401

# ... (coloque todas as outras rotas que você já tinha: /api/dashboard, /api/clientes, etc.)
# Para evitar repetir todo o código, sugiro copiar as rotas do seu app.py atual.
# Apenas as que estão aqui são exemplos; mantenha as que você já tem.

# -------------------------------------------------------------
# Inicialização
# -------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
