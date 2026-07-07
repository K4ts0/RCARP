from __future__ import annotations
import os
import json
import sys
import time
from pathlib import Path
from flask import Flask, request, session, jsonify, send_file
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect
from datetime import datetime, date

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
INDEX_HTML = BASE_DIR / "index.html"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-lavagem-2024")

# ============================================================
# CONFIGURAÇÃO DO BANCO DE DADOS (PostgreSQL ou SQLite fallback)
# ============================================================
# ⚠️ IMPORTANTE: No Supabase, use o SHARED POOLER (Supavisor) em SESSION MODE
# para conectar do Render (IPv4-only). NÃO use o Dedicated Pooler (PgBouncer)
# na porta 6543 com db.projectref.supabase.co — esse resolve para IPv6 e
# quebra no Render com "Network is unreachable".
#
# ✅ FORMATO CORRETO da DATABASE_URL no Render:
# postgresql://postgres.PROJECT_REF:SENHA@aws-0-REGION.pooler.supabase.com:5432/postgres
#
# ❌ FORMATO INCORRETO (IPv6, não funciona no Render):
# postgresql://postgres:SENHA@db.PROJECT_REF.supabase.co:6543/postgres
#
# Pegue a string correta em: Supabase Dashboard → Project Settings → Database
# → "Connection pooling" → "Session mode"
# ============================================================

database_url = os.environ.get("DATABASE_URL")

if database_url:
    url_limpa = database_url.strip().replace('(', '').replace(')', '').strip()

    # Corrigir prefixo postgres:// para postgresql://
    if url_limpa.startswith("postgres://"):
        url_limpa = url_limpa.replace("postgres://", "postgresql://", 1)

    # Para psycopg v3, usar postgresql+psycopg://
    if url_limpa.startswith("postgresql://") and not url_limpa.startswith("postgresql+psycopg://"):
        url_limpa = url_limpa.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = url_limpa
    print(f"🔄 Usando PostgreSQL: {url_limpa[:70]}...", flush=True)
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    print("✅ Usando SQLite local", flush=True)

# Configurações otimizadas para Supavisor (Shared Pooler) no Render
# pool_size baixo porque o Supavisor já gerencia o pool do lado dele
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 280,        # Menor que 300s (timeout do Supavisor)
    "pool_pre_ping": True,      # Verifica conexão antes de usar
    "pool_size": 2,             # Baixo — Supavisor gerencia o pool real
    "max_overflow": 3,          # Overflow conservador
    "pool_timeout": 30,         # Timeout de espera por conexão
    "connect_args": {
        "connect_timeout": 10,
        "sslmode": "require"    # Supabase exige SSL obrigatoriamente
    }
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

bcrypt = Bcrypt(app)
db = SQLAlchemy(app)

# ============================================================
# MODELOS
# ============================================================
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    nivel = db.Column(db.String(20), default="funcionario")
    nome = db.Column(db.String(100), default="")

    def set_password(self, raw):
        self.password_hash = bcrypt.generate_password_hash(raw).decode()

    def check_password(self, raw):
        return bcrypt.check_password_hash(self.password_hash, raw)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'nome': self.nome or self.username,
            'nivel': self.nivel,
            'is_admin': self.is_admin
        }

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

    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'telefone': self.telefone or '',
            'placa': self.placa,
            'veiculo': self.veiculo,
            'plano': self.plano,
            'mensalidade': float(self.mensalidade or 0),
            'inicio': self.inicio.isoformat() if self.inicio else '',
            'vencimento': self.vencimento.isoformat() if self.vencimento else '',
            'status': self.status,
            'observacoes': self.observacoes or ''
        }

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

    def to_dict(self):
        return {
            'id': self.id,
            'produto': self.produto,
            'categoria': self.categoria,
            'unidade': self.unidade,
            'quantidade': float(self.quantidade or 0),
            'estoqueMin': float(self.estoque_min or 0),
            'preco': float(self.preco or 0.0)
        }

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

    def to_dict(self):
        return {
            'id': self.id,
            'data': self.data.isoformat() if self.data else '',
            'clienteId': self.cliente_id,
            'clienteNome': self.cliente_nome,
            'placa': self.placa,
            'servico': self.servico,
            'funcionario': self.funcionario,
            'tipo': self.tipo,
            'preco': float(self.preco or 0),
            'observacoes': self.observacoes or '',
            'produtosUtilizados': json.loads(self.produtos_utilizados) if self.produtos_utilizados else []
        }

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def logged_in():
    return bool(session.get("uid"))

def init_db():
    """Cria tabelas e usuário admin, se não existirem."""
    with app.app_context():
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Testa conexão antes de criar tabelas
                db.session.execute(text('SELECT 1'))
                print("✅ Conexão com banco estabelecida", flush=True)

                db.create_all()
                print("✅ Tabelas criadas/verificadas", flush=True)

                if not User.query.first():
                    admin = User(
                        username="admin",
                        nome="Administrador",
                        nivel="administrador",
                        is_admin=True
                    )
                    admin.set_password("1234")
                    db.session.add(admin)
                    db.session.commit()
                    print("✅ Usuário admin criado: admin / 1234", flush=True)
                else:
                    print("✅ Usuários já existem", flush=True)

                if not Produto.query.first():
                    produtos_exemplo = [
                        Produto(produto='Shampoo Automotivo', categoria='Limpeza', unidade='Litro', quantidade=10, estoque_min=5, preco=25.50),
                        Produto(produto='Cera Líquida', categoria='Limpeza', unidade='Unidade', quantidade=15, estoque_min=3, preco=18.00),
                        Produto(produto='Limpador de Pneu', categoria='Limpeza', unidade='Unidade', quantidade=20, estoque_min=5, preco=12.00),
                        Produto(produto='Pano de Microfibra', categoria='Acessório', unidade='Unidade', quantidade=50, estoque_min=10, preco=8.50),
                    ]
                    for p in produtos_exemplo:
                        db.session.add(p)
                    db.session.commit()
                    print("✅ Produtos de exemplo criados", flush=True)
                else:
                    print("✅ Produtos já existem", flush=True)

                return True

            except Exception as e:
                print(f"⚠️ Erro na inicialização (tentativa {attempt + 1}/{max_retries}): {e}", flush=True)
                db.session.rollback()
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print("❌ Falha ao inicializar banco após todas as tentativas", flush=True)
        return False

# ============================================================
# INICIALIZAÇÃO DO BANCO — CORREÇÃO CRÍTICA PARA RENDER
# ============================================================
# No Render, o Gunicorn importa o módulo sem executar __main__.
# Usamos before_request como fallback garantido.
# ============================================================
_db_initialized = False

@app.before_request
def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        print("🔧 Primeira requisição — inicializando banco...", flush=True)
        init_db()
        _db_initialized = True

# Tenta inicializar no import (funciona em desenvolvimento local)
try:
    init_db()
    _db_initialized = True
except Exception as e:
    print(f"⚠️ init_db no import falhou (normal no Render): {e}", flush=True)

# ============================================================
# ROTAS
# ============================================================
@app.route("/")
def home():
    """Serve index.html diretamente da pasta raiz."""
    if INDEX_HTML.exists():
        return send_file(str(INDEX_HTML))
    return "<h1>Way For System</h1><p>index.html não encontrado. Coloque o arquivo na mesma pasta do app.py</p>", 200

@app.route("/favicon.ico")
def favicon():
    return "", 204

# -------------------------------------------------------------
# AUTENTICAÇÃO
# -------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Dados não fornecidos'}), 400

        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'success': False, 'message': 'Usuário e senha obrigatórios'}), 400

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session["uid"] = user.id
            session["username"] = user.username
            session["nivel"] = user.nivel
            return jsonify({
                'success': True,
                'user': {
                    'nome': user.nome or user.username,
                    'username': user.username,
                    'nivel': user.nivel
                }
            })

        return jsonify({'success': False, 'message': 'Credenciais inválidas'}), 401
    except Exception as e:
        print(f"Erro no login: {e}", flush=True)
        return jsonify({'success': False, 'message': f'Erro interno: {str(e)}'}), 500

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({'success': True})

# -------------------------------------------------------------
# DASHBOARD
# -------------------------------------------------------------
@app.route("/api/dashboard")
def api_dashboard():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    try:
        hoje = date.today()

        clientes = Cliente.query.all()
        for cliente in clientes:
            if cliente.vencimento and cliente.vencimento < hoje and cliente.status == 'Pago':
                cliente.status = 'Vencido'
        db.session.commit()

        clientes_ativos = Cliente.query.filter_by(status="Pago").count()
        inadimplentes = Cliente.query.filter_by(status="Vencido").count()

        receita_mensalidades = db.session.query(db.func.sum(Cliente.mensalidade)).filter_by(status="Pago").scalar() or 0
        receita_lavagens_avulsas = db.session.query(db.func.sum(Lavagem.preco)).filter_by(tipo="avulsa").scalar() or 0
        receita_total = receita_mensalidades + receita_lavagens_avulsas
        a_receber = db.session.query(db.func.sum(Cliente.mensalidade)).filter(Cliente.status != "Pago").scalar() or 0
        lavagens_avulsas = Lavagem.query.filter_by(tipo="avulsa").count()

        custo_produtos = 0.0
        lavagens_com_produtos = Lavagem.query.filter(Lavagem.produtos_utilizados.isnot(None)).all()
        for lavagem in lavagens_com_produtos:
            if lavagem.produtos_utilizados:
                try:
                    produtos_utilizados = json.loads(lavagem.produtos_utilizados)
                    for produto_usado in produtos_utilizados:
                        produto = Produto.query.get(produto_usado.get('produtoId'))
                        if produto:
                            custo_produtos += produto_usado.get('quantidade', 0) * produto.preco
                except Exception:
                    pass

        lucro_total = receita_total - custo_produtos

        ultimas_lavagens = Lavagem.query.order_by(Lavagem.data.desc()).limit(5).all()

        return jsonify({
            'stats': {
                'clientesAtivos': clientes_ativos,
                'receitaTotal': float(receita_total),
                'inadimplentes': inadimplentes,
                'aReceber': float(a_receber),
                'lavagensAvulsas': lavagens_avulsas,
                'lucroTotal': float(lucro_total)
            },
            'ultimasLavagens': [
                {
                    'data': lavagem.data.isoformat() if lavagem.data else '',
                    'clienteNome': lavagem.cliente_nome,
                    'placa': lavagem.placa,
                    'servico': lavagem.servico,
                    'funcionario': lavagem.funcionario,
                    'tipo': lavagem.tipo
                }
                for lavagem in ultimas_lavagens
            ]
        })
    except Exception as e:
        print(f"Erro no dashboard: {e}", flush=True)
        return jsonify({'error': f'Erro no dashboard: {str(e)}'}), 500

# ========== CLIENTES ==========
@app.route("/api/clientes")
def api_clientes():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    try:
        clientes = Cliente.query.all()
        return jsonify({'clientes': [c.to_dict() for c in clientes]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/clientes", methods=["POST"])
def api_criar_cliente():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    data = request.get_json()
    try:
        cliente = Cliente(
            nome=data['nome'],
            telefone=data.get('telefone', ''),
            placa=data['placa'],
            veiculo=data.get('veiculo', 'Carro'),
            plano=data.get('plano', 'Mensal'),
            mensalidade=float(data.get('mensalidade', 500)),
            inicio=datetime.fromisoformat(data['inicio']).date() if data.get('inicio') else date.today(),
            vencimento=datetime.fromisoformat(data['vencimento']).date() if data.get('vencimento') else date.today(),
            status=data.get('status', 'Pendente'),
            observacoes=data.get('observacoes', '')
        )
        db.session.add(cliente)
        db.session.commit()
        return jsonify({'success': True, 'id': cliente.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/clientes/<int:cliente_id>", methods=["PUT"])
def api_atualizar_cliente(cliente_id):
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    data = request.get_json()
    cliente = Cliente.query.get_or_404(cliente_id)
    try:
        cliente.nome = data['nome']
        cliente.telefone = data.get('telefone', '')
        cliente.placa = data['placa']
        cliente.veiculo = data.get('veiculo', 'Carro')
        cliente.plano = data.get('plano', 'Mensal')
        cliente.mensalidade = float(data.get('mensalidade', 500))
        cliente.inicio = datetime.fromisoformat(data['inicio']).date() if data.get('inicio') else cliente.inicio
        cliente.vencimento = datetime.fromisoformat(data['vencimento']).date() if data.get('vencimento') else cliente.vencimento
        cliente.status = data.get('status', 'Pendente')
        cliente.observacoes = data.get('observacoes', '')
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/clientes/<int:cliente_id>", methods=["DELETE"])
def api_excluir_cliente(cliente_id):
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    cliente = Cliente.query.get_or_404(cliente_id)
    try:
        db.session.delete(cliente)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ========== LAVAGENS ==========
@app.route("/api/lavagens")
def api_lavagens():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    try:
        lavagens = Lavagem.query.all()
        return jsonify({'lavagens': [l.to_dict() for l in lavagens]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/lavagens", methods=["POST"])
def api_criar_lavagem():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    data = request.get_json()
    try:
        lavagem = Lavagem(
            data=datetime.fromisoformat(data['data']).date() if data.get('data') else date.today(),
            cliente_id=data.get('clienteId'),
            cliente_nome=data['clienteNome'],
            placa=data['placa'],
            servico=data['servico'],
            funcionario=data['funcionario'],
            tipo=data['tipo'],
            preco=float(data.get('preco', 0)),
            observacoes=data.get('observacoes', ''),
            produtos_utilizados=json.dumps(data.get('produtosUtilizados', []))
        )

        for pu in data.get('produtosUtilizados', []):
            produto = Produto.query.get(pu.get('produtoId'))
            if produto:
                produto.quantidade -= pu.get('quantidade', 0)

        db.session.add(lavagem)
        db.session.commit()
        return jsonify({'success': True, 'id': lavagem.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/lavagens/<int:lavagem_id>", methods=["DELETE"])
def api_excluir_lavagem(lavagem_id):
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    lavagem = Lavagem.query.get_or_404(lavagem_id)
    try:
        if lavagem.produtos_utilizados:
            for pu in json.loads(lavagem.produtos_utilizados):
                produto = Produto.query.get(pu.get('produtoId'))
                if produto:
                    produto.quantidade += pu.get('quantidade', 0)

        db.session.delete(lavagem)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ========== PRODUTOS ==========
@app.route("/api/produtos")
def api_produtos():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    try:
        produtos = Produto.query.all()
        return jsonify({'produtos': [p.to_dict() for p in produtos]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/produtos", methods=["POST"])
def api_criar_produto():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    data = request.get_json()
    try:
        produto = Produto(
            produto=data['produto'],
            categoria=data.get('categoria', 'Limpeza'),
            unidade=data.get('unidade', 'Unidade'),
            quantidade=float(data.get('quantidade', 0)),
            estoque_min=float(data.get('estoqueMin', 0)),
            preco=float(data.get('preco', 0))
        )
        db.session.add(produto)
        db.session.commit()
        return jsonify({'success': True, 'id': produto.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/produtos/<int:produto_id>", methods=["PUT"])
def api_atualizar_produto(produto_id):
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    data = request.get_json()
    produto = Produto.query.get_or_404(produto_id)
    try:
        produto.produto = data['produto']
        produto.categoria = data.get('categoria', 'Limpeza')
        produto.unidade = data.get('unidade', 'Unidade')
        produto.quantidade = float(data.get('quantidade', 0))
        produto.estoque_min = float(data.get('estoqueMin', 0))
        produto.preco = float(data.get('preco', 0))
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route("/api/produtos/<int:produto_id>", methods=["DELETE"])
def api_excluir_produto(produto_id):
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    produto = Produto.query.get_or_404(produto_id)
    try:
        db.session.delete(produto)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ========== FINANCEIRO ==========
@app.route("/api/financeiro")
def api_financeiro():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    try:
        ano_atual = datetime.now().year
        meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        receitas_mensais = []
        for mes in range(12):
            receita_mensalidades = db.session.query(db.func.sum(Cliente.mensalidade)).filter(
                db.extract('month', Cliente.inicio) == mes + 1,
                db.extract('year', Cliente.inicio) == ano_atual,
                Cliente.status == 'Pago'
            ).scalar() or 0
            receita_lavagens = db.session.query(db.func.sum(Lavagem.preco)).filter(
                db.extract('month', Lavagem.data) == mes + 1,
                db.extract('year', Lavagem.data) == ano_atual,
                Lavagem.tipo == 'avulsa'
            ).scalar() or 0
            receitas_mensais.append(float(receita_mensalidades + receita_lavagens))
        return jsonify({'receitasMensais': receitas_mensais, 'meses': meses})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== DEBUG ==========
@app.route("/api/debug/db")
def debug_db():
    try:
        db.session.execute(text('SELECT 1'))
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        user_count = User.query.count()
        produto_count = Produto.query.count()
        return jsonify({
            "status": "success",
            "tables": tables,
            "user_count": user_count,
            "produto_count": produto_count,
            "database_url": app.config["SQLALCHEMY_DATABASE_URI"][:70] + "..."
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# ============================================================
# INICIALIZAÇÃO DO SERVIDOR
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
