// database.js
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

class Database {
    constructor() {
        this.db = new sqlite3.Database(path.join(__dirname, 'rpcar.db'), (err) => {
            if (err) {
                console.error('Erro ao conectar com o banco de dados:', err);
            } else {
                console.log('Conectado ao banco de dados SQLite.');
                this.criarTabelas();
            }
        });
    }

    criarTabelas() {
        // Tabela de usuários
        this.db.run(`CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nome TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )`);

        // Tabela de clientes
        this.db.run(`CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            placa TEXT NOT NULL UNIQUE,
            veiculo TEXT NOT NULL,
            plano TEXT NOT NULL,
            mensalidade REAL NOT NULL,
            inicio DATE NOT NULL,
            vencimento DATE NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente',
            observacoes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )`);

        // Tabela de produtos (estoque)
        this.db.run(`CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidade TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            estoque_min INTEGER NOT NULL,
            preco REAL NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )`);

        // Tabela de lavagens
        this.db.run(`CREATE TABLE IF NOT EXISTS lavagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            cliente_id INTEGER,
            cliente_nome TEXT NOT NULL,
            placa TEXT NOT NULL,
            servico TEXT NOT NULL,
            funcionario TEXT NOT NULL,
            tipo TEXT NOT NULL,
            preco REAL DEFAULT 0,
            observacoes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )`);

        // Tabela de produtos utilizados nas lavagens
        this.db.run(`CREATE TABLE IF NOT EXISTS produtos_utilizados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lavagem_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            quantidade INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lavagem_id) REFERENCES lavagens (id) ON DELETE CASCADE,
            FOREIGN KEY (produto_id) REFERENCES produtos (id)
        )`);

        // Inserir usuário admin padrão
        this.db.get("SELECT COUNT(*) as count FROM usuarios", (err, row) => {
            if (err) return;
            if (row.count === 0) {
                this.db.run(
                    "INSERT INTO usuarios (username, password, nome) VALUES (?, ?, ?)",
                    ['admin', '1234', 'Administrador']
                );
            }
        });

        // Inserir alguns produtos de exemplo
        this.db.get("SELECT COUNT(*) as count FROM produtos", (err, row) => {
            if (err) return;
            if (row.count === 0) {
                const produtosExemplo = [
                    ['Shampoo Automotivo', 'Limpeza', 'Litro', 10, 5, 25.50],
                    ['Cera Líquida', 'Limpeza', 'Unidade', 15, 3, 18.00],
                    ['Limpador de Pneu', 'Limpeza', 'Unidade', 20, 5, 12.00],
                    ['Pano de Microfibra', 'Acessório', 'Unidade', 50, 10, 8.50]
                ];
                
                const stmt = this.db.prepare(
                    "INSERT INTO produtos (produto, categoria, unidade, quantidade, estoque_min, preco) VALUES (?, ?, ?, ?, ?, ?)"
                );
                
                produtosExemplo.forEach(produto => {
                    stmt.run(produto);
                });
                stmt.finalize();
            }
        });
    }

    // Métodos para Usuários
    buscarUsuario(username) {
        return new Promise((resolve, reject) => {
            this.db.get("SELECT * FROM usuarios WHERE username = ?", [username], (err, row) => {
                if (err) reject(err);
                else resolve(row);
            });
        });
    }

    // Métodos para Clientes
    buscarClientes() {
        return new Promise((resolve, reject) => {
            this.db.all("SELECT * FROM clientes ORDER BY created_at DESC", (err, rows) => {
                if (err) reject(err);
                else resolve(rows);
            });
        });
    }

    buscarClientePorId(id) {
        return new Promise((resolve, reject) => {
            this.db.get("SELECT * FROM clientes WHERE id = ?", [id], (err, row) => {
                if (err) reject(err);
                else resolve(row);
            });
        });
    }

    salvarCliente(cliente) {
        return new Promise((resolve, reject) => {
            const { id, nome, telefone, placa, veiculo, plano, mensalidade, inicio, vencimento, status, observacoes } = cliente;
            
            if (id) {
                // Atualizar cliente existente
                this.db.run(
                    `UPDATE clientes SET 
                     nome = ?, telefone = ?, placa = ?, veiculo = ?, plano = ?, 
                     mensalidade = ?, inicio = ?, vencimento = ?, status = ?, 
                     observacoes = ?, updated_at = CURRENT_TIMESTAMP 
                     WHERE id = ?`,
                    [nome, telefone, placa, veiculo, plano, mensalidade, inicio, vencimento, status, observacoes, id],
                    function(err) {
                        if (err) reject(err);
                        else resolve({ id: id });
                    }
                );
            } else {
                // Inserir novo cliente
                this.db.run(
                    `INSERT INTO clientes 
                     (nome, telefone, placa, veiculo, plano, mensalidade, inicio, vencimento, status, observacoes) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                    [nome, telefone, placa, veiculo, plano, mensalidade, inicio, vencimento, status, observacoes],
                    function(err) {
                        if (err) reject(err);
                        else resolve({ id: this.lastID });
                    }
                );
            }
        });
    }

    excluirCliente(id) {
        return new Promise((resolve, reject) => {
            this.db.run("DELETE FROM clientes WHERE id = ?", [id], function(err) {
                if (err) reject(err);
                else resolve({ changes: this.changes });
            });
        });
    }

    // Métodos para Produtos
    buscarProdutos() {
        return new Promise((resolve, reject) => {
            this.db.all("SELECT * FROM produtos ORDER BY created_at DESC", (err, rows) => {
                if (err) reject(err);
                else resolve(rows);
            });
        });
    }

    buscarProdutoPorId(id) {
        return new Promise((resolve, reject) => {
            this.db.get("SELECT * FROM produtos WHERE id = ?", [id], (err, row) => {
                if (err) reject(err);
                else resolve(row);
            });
        });
    }

    salvarProduto(produto) {
        return new Promise((resolve, reject) => {
            const { id, produto: nome, categoria, unidade, quantidade, estoque_min, preco } = produto;
            
            if (id) {
                // Atualizar produto existente
                this.db.run(
                    `UPDATE produtos SET 
                     produto = ?, categoria = ?, unidade = ?, quantidade = ?, 
                     estoque_min = ?, preco = ?, updated_at = CURRENT_TIMESTAMP 
                     WHERE id = ?`,
                    [nome, categoria, unidade, quantidade, estoque_min, preco, id],
                    function(err) {
                        if (err) reject(err);
                        else resolve({ id: id });
                    }
                );
            } else {
                // Inserir novo produto
                this.db.run(
                    `INSERT INTO produtos (produto, categoria, unidade, quantidade, estoque_min, preco) 
                     VALUES (?, ?, ?, ?, ?, ?)`,
                    [nome, categoria, unidade, quantidade, estoque_min, preco],
                    function(err) {
                        if (err) reject(err);
                        else resolve({ id: this.lastID });
                    }
                );
            }
        });
    }

    excluirProduto(id) {
        return new Promise((resolve, reject) => {
            this.db.run("DELETE FROM produtos WHERE id = ?", [id], function(err) {
                if (err) reject(err);
                else resolve({ changes: this.changes });
            });
        });
    }

    // Métodos para Lavagens
    buscarLavagens() {
        return new Promise((resolve, reject) => {
            this.db.all(`
                SELECT l.*, 
                GROUP_CONCAT(pu.produto_id || ':' || pu.quantidade) as produtos_utilizados
                FROM lavagens l
                LEFT JOIN produtos_utilizados pu ON l.id = pu.lavagem_id
                GROUP BY l.id
                ORDER BY l.data DESC, l.created_at DESC
            `, (err, rows) => {
                if (err) reject(err);
                else {
                    // Processar produtos utilizados
                    const lavagens = rows.map(lavagem => {
                        if (lavagem.produtos_utilizados) {
                            lavagem.produtosUtilizados = lavagem.produtos_utilizados.split(',').map(item => {
                                const [produtoId, quantidade] = item.split(':');
                                return {
                                    produtoId: parseInt(produtoId),
                                    quantidade: parseInt(quantidade)
                                };
                            });
                        } else {
                            lavagem.produtosUtilizados = [];
                        }
                        delete lavagem.produtos_utilizados;
                        return lavagem;
                    });
                    resolve(lavagens);
                }
            });
        });
    }

    salvarLavagem(lavagem) {
        return new Promise((resolve, reject) => {
            const { data, clienteId, clienteNome, placa, servico, funcionario, tipo, preco, observacoes, produtosUtilizados } = lavagem;
            
            this.db.run(
                `INSERT INTO lavagens 
                 (data, cliente_id, cliente_nome, placa, servico, funcionario, tipo, preco, observacoes) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [data, clienteId, clienteNome, placa, servico, funcionario, tipo, preco, observacoes],
                function(err) {
                    if (err) {
                        reject(err);
                    } else {
                        const lavagemId = this.lastID;
                        
                        // Salvar produtos utilizados
                        if (produtosUtilizados && produtosUtilizados.length > 0) {
                            const stmt = this.db.prepare(
                                "INSERT INTO produtos_utilizados (lavagem_id, produto_id, quantidade) VALUES (?, ?, ?)"
                            );
                            
                            produtosUtilizados.forEach(produto => {
                                stmt.run([lavagemId, produto.produtoId, produto.quantidade]);
                                
                                // Atualizar estoque
                                this.db.run(
                                    "UPDATE produtos SET quantidade = quantidade - ? WHERE id = ?",
                                    [produto.quantidade, produto.produtoId]
                                );
                            });
                            
                            stmt.finalize();
                        }
                        
                        resolve({ id: lavagemId });
                    }
                }.bind(this)
            );
        });
    }

    excluirLavagem(id) {
        return new Promise((resolve, reject) => {
            // Primeiro, buscar os produtos utilizados para restaurar o estoque
            this.db.all(
                "SELECT produto_id, quantidade FROM produtos_utilizados WHERE lavagem_id = ?",
                [id],
                (err, produtos) => {
                    if (err) {
                        reject(err);
                        return;
                    }
                    
                    // Restaurar estoque
                    produtos.forEach(produto => {
                        this.db.run(
                            "UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?",
                            [produto.quantidade, produto.produto_id]
                        );
                    });
                    
                    // Agora excluir a lavagem (os produtos_utilizados serão excluídos em cascade)
                    this.db.run("DELETE FROM lavagens WHERE id = ?", [id], function(err) {
                        if (err) reject(err);
                        else resolve({ changes: this.changes });
                    });
                }
            );
        });
    }

    // Métodos para relatórios e estatísticas
    buscarEstatisticas() {
        return new Promise((resolve, reject) => {
            const estatisticas = {};
            
            // Clientes ativos
            this.db.get(
                "SELECT COUNT(*) as count FROM clientes WHERE status = 'Pago'",
                (err, row) => {
                    if (err) reject(err);
                    else {
                        estatisticas.clientesAtivos = row.count;
                        
                        // Inadimplentes
                        this.db.get(
                            "SELECT COUNT(*) as count FROM clientes WHERE status = 'Vencido'",
                            (err, row) => {
                                if (err) reject(err);
                                else {
                                    estatisticas.inadimplentes = row.count;
                                    
                                    // Receita total
                                    this.db.get(`
                                        SELECT 
                                            COALESCE(SUM(mensalidade), 0) as receitaMensalidades,
                                            COALESCE(SUM(CASE WHEN status != 'Pago' THEN mensalidade ELSE 0 END), 0) as aReceber
                                        FROM clientes
                                    `, (err, row) => {
                                        if (err) reject(err);
                                        else {
                                            estatisticas.receitaMensalidades = row.receitaMensalidades;
                                            estatisticas.aReceber = row.aReceber;
                                            
                                            // Lavagens avulsas
                                            this.db.get(`
                                                SELECT 
                                                    COUNT(*) as count,
                                                    COALESCE(SUM(preco), 0) as receita
                                                FROM lavagens 
                                                WHERE tipo = 'avulsa'
                                            `, (err, row) => {
                                                if (err) reject(err);
                                                else {
                                                    estatisticas.lavagensAvulsas = row.count;
                                                    estatisticas.receitaLavagensAvulsas = row.receita;
                                                    
                                                    // Custo total dos produtos
                                                    this.db.get(
                                                        "SELECT COALESCE(SUM(quantidade * preco), 0) as custoTotal FROM produtos",
                                                        (err, row) => {
                                                            if (err) reject(err);
                                                            else {
                                                                estatisticas.custoTotalProdutos = row.custoTotal;
                                                                resolve(estatisticas);
                                                            }
                                                        }
                                                    );
                                                }
                                            });
                                        }
                                    });
                                }
                            }
                        );
                    }
                }
            );
        });
    }

    fechar() {
        this.db.close();
    }
}

module.exports = Database;