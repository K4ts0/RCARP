from __future__ import annotations
import os
import json
from pathlib import Path
from flask import Flask, render_template, request, session, jsonify
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, inspect
from datetime import datetime, date

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

# -------------------------------------------------------------
# Configuração do banco de dados (usando psycopg 3)
# -------------------------------------------------------------
database_url = os.environ.get("DATABASE_URL")

if database_url:
    url_limpa = database_url.strip().replace('(', '').replace(')', '').strip()
    if url_limpa.startswith("postgres://"):
        url_limpa = url_limpa.replace("postgres://", "postgresql://", 1)
    # CORREÇÃO: usa o driver psycopg (versão 3) em vez do psycopg2
    if url_limpa.startswith("postgresql://"):
        url_limpa = url_limpa.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = url_limpa
    print(f"🔄 Conectando ao Supabase: {url_limpa.split('@')[1] if '@' in url_limpa else 'URL configurada'}")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    print("✅ Usando SQLite local (fallback)")

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

bcrypt = Bcrypt(app)

# -------------------------------------------------------------
# Inicialização do SQLAlchemy (sem criar engine ainda)
# -------------------------------------------------------------
db = SQLAlchemy()       # não passa app
db.init_app(app)        # vincula ao app

# -------------------------------------------------------------
# MODELOS
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
    produtos_utilizados = db.Column(db.Text)  # JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------------------
def logged_in():
    return bool(session.get("uid"))

def init_db():
    """Cria tabelas e usuário admin, se não existirem."""
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
# ROTAS DA API
# -------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/login", methods=["POST"])
def api_login():
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
                'nome': user.username,
                'username': user.username,
                'nivel': user.nivel
            }
        })
    return jsonify({'success': False, 'message': 'Credenciais inválidas'}), 401

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({'success': True})

@app.route("/api/dashboard")
def api_dashboard():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    try:
        hoje = date.today()
        clientes = Cliente.query.all()
        for cliente in clientes:
            if cliente.status == 'Pago' and cliente.vencimento < hoje:
                cliente.status = 'Vencido'
            elif cliente.status == 'Pendente' and cliente.vencimento < hoje:
                cliente.status = 'Vencido'
        db.session.commit()
        clientes_ativos = Cliente.query.filter_by(status="Pago").count()
        inadimplentes = Cliente.query.filter_by(status="Vencido").count()
        receita_mensalidades = db.session.query(db.func.sum(Cliente.mensalidade)).filter_by(status="Pago").scalar() or 0
        receita_lavagens_avulsas = db.session.query(db.func.sum(Lavagem.preco)).filter_by(tipo="avulsa").scalar() or 0
        receita_total = receita_mensalidades + receita_lavagens_avulsas
        a_receber = db.session.query(db.func.sum(Cliente.mensalidade)).filter(Cliente.status != "Pago").scalar() or 0
        lavagens_avulsas = Lavagem.query.filter_by(tipo="avulsa").count()
        custo_produtos = 0
        lavagens_com_produtos = Lavagem.query.filter(Lavagem.produtos_utilizados.isnot(None)).all()
        for lavagem in lavagens_com_produtos:
            if lavagem.produtos_utilizados:
                try:
                    produtos_utilizados = json.loads(lavagem.produtos_utilizados)
                    for produto_usado in produtos_utilizados:
                        produto = Produto.query.get(produto_usado['produtoId'])
                        if produto:
                            custo_produtos += produto_usado['quantidade'] * produto.preco
                except:
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
                    'data': lavagem.data.isoformat(),
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
        return jsonify({'error': f'Erro no dashboard: {str(e)}'}), 500

# ========== ROTAS DE CLIENTES ==========
@app.route("/api/clientes")
def api_clientes():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    clientes = Cliente.query.all()
    return jsonify({
        'clientes': [
            {
                'id': c.id,
                'nome': c.nome,
                'telefone': c.telefone,
                'placa': c.placa,
                'veiculo': c.veiculo,
                'plano': c.plano,
                'mensalidade': float(c.mensalidade),
                'inicio': c.inicio.isoformat(),
                'vencimento': c.vencimento.isoformat(),
                'status': c.status,
                'observacoes': c.observacoes
            } for c in clientes
        ]
    })

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
            inicio=datetime.fromisoformat(data['inicio']).date(),
            vencimento=datetime.fromisoformat(data['vencimento']).date(),
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
        cliente.inicio = datetime.fromisoformat(data['inicio']).date()
        cliente.vencimento = datetime.fromisoformat(data['vencimento']).date()
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

# ========== ROTAS DE LAVAGENS ==========
@app.route("/api/lavagens")
def api_lavagens():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    lavagens = Lavagem.query.all()
    return jsonify({
        'lavagens': [
            {
                'id': l.id,
                'data': l.data.isoformat(),
                'clienteId': l.cliente_id,
                'clienteNome': l.cliente_nome,
                'placa': l.placa,
                'servico': l.servico,
                'funcionario': l.funcionario,
                'tipo': l.tipo,
                'preco': float(l.preco),
                'observacoes': l.observacoes,
                'produtosUtilizados': json.loads(l.produtos_utilizados) if l.produtos_utilizados else []
            } for l in lavagens
        ]
    })

@app.route("/api/lavagens", methods=["POST"])
def api_criar_lavagem():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    data = request.get_json()
    try:
        lavagem = Lavagem(
            data=datetime.fromisoformat(data['data']).date(),
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
            produto = Produto.query.get(pu['produtoId'])
            if produto:
                produto.quantidade -= pu['quantidade']
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
                produto = Produto.query.get(pu['produtoId'])
                if produto:
                    produto.quantidade += pu['quantidade']
        db.session.delete(lavagem)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

# ========== ROTAS DE PRODUTOS ==========
@app.route("/api/produtos")
def api_produtos():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
    produtos = Produto.query.all()
    return jsonify({
        'produtos': [
            {
                'id': p.id,
                'produto': p.produto,
                'categoria': p.categoria,
                'unidade': p.unidade,
                'quantidade': p.quantidade,
                'estoqueMin': p.estoque_min,
                'preco': float(p.preco)
            } for p in produtos
        ]
    })

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

# ========== ROTA FINANCEIRO ==========
@app.route("/api/financeiro")
def api_financeiro():
    if not logged_in():
        return jsonify({'error': 'Não autenticado'}), 401
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

# ========== DEBUG ==========
@app.route("/api/debug/db")
def debug_db():
    try:
        db.session.execute(text('SELECT 1'))
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        user_count = User.query.count()
        return jsonify({
            "status": "success",
            "tables": tables,
            "user_count": user_count,
            "database_url": app.config["SQLALCHEMY_DATABASE_URI"][:50] + "..."
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# ========== INICIALIZAÇÃO (apenas quando executado diretamente) ==========
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
