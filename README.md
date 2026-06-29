# 🚗 Way For System — Gestão Automotiva

Sistema web completo para administração de **lavagem de carros e pequenas oficinas**. Controle de clientes, lavagens, estoque, vendas de produtos, prestação de serviços, relatórios e painel administrativo com níveis de acesso.

🔗 **Acesse o sistema online:** [Seu link do Render aqui]

---

## Funcionalidades Principais

| Módulo | Descrição |
|:------:|:----------|
| **Dashboard** | Visão geral com estatísticas em tempo real |
| **Clientes** | Cadastro de assinantes com planos e mensalidades |
| **Lavagens** | Registro de lavagens (assinantes e avulsas) |
| **Estoque** | Controle de produtos com alerta de estoque mínimo |
| **Vendas** | Venda de produtos com baixa automática no estoque |
| **Serviços** | Prestação de serviços (polimento, cristalização, etc.) |
| **Relatórios** | Relatórios filtráveis por período com impressão |
| **Admin** | Gerenciamento de usuários e níveis de acesso |

---

## ✨ Funcionalidades Detalhadas

### 📊 Dashboard
- ✅ **Clientes Ativos** — Total de assinantes cadastrados
- ✅ **Receita Total** — Soma de mensalidades e lavagens avulsas
- ✅ **Inadimplentes** — Clientes com pagamento vencido
- ✅ **A Receber** — Valor total de mensalidades pendentes
- ✅ **Lavagens Avulsas** — Quantidade de lavagens avulsas realizadas
- ✅ **Lucro Estimado** — Projeção de receita total
- ✅ **Últimas Lavagens** — Tabela com os registros mais recentes

### 👥 Gestão de Clientes
- ✅ Cadastro completo: nome, telefone, placa, tipo de veículo
- ✅ **Planos**: Mensal, Trimestral, Semestral, Anual
- ✅ **Mensalidade** com valor configurável
- ✅ **Datas de início e vencimento** automáticas
- ✅ **Status de pagamento**: Pago, Pendente, Vencido
- ✅ **Validação de placa** — Impede cadastro duplicado
- ✅ Edição e exclusão de clientes

### 🧼 Controle de Lavagens
- ✅ **Lavagens de Assinantes** — Vinculadas a clientes cadastrados
- ✅ **Lavagens Avulsas** — Com preço definido no momento
- ✅ **Tipos de serviço**: Simples, Completa, Com Cera, Polimento, Higienização
- ✅ **Produtos utilizados** — Baixa automática no estoque
- ✅ **Funcionário responsável**
- ✅ Observações por lavagem

### 📦 Controle de Estoque
- ✅ Cadastro de produtos: nome, categoria, unidade, quantidade
- ✅ **Estoque mínimo** com alerta visual
- ✅ **Preço unitário** e valor total em estoque
- ✅ Categorias: Limpeza, Químico, Acessório, Ferragem, Outros
- ✅ Edição e exclusão de produtos

### 🛒 Venda de Produtos
- ✅ Venda direta com seleção de cliente (assinante ou avulso)
- ✅ Seleção de produto com estoque disponível
- ✅ **Baixa automática no estoque** ao registrar venda
- ✅ Valor unitário e quantidade
- ✅ Funcionário responsável

### 🔧 Prestação de Serviços
- ✅ Tipos: Polimento, Cristalização, Higienização, Recuperação de Faróis, Tratamento de Couro, Plotagem
- ✅ Descrição detalhada do serviço
- ✅ Valor do serviço
- ✅ **Status do serviço**: Pendente, Em Andamento, Concluído
- ✅ Vinculação a cliente e placa

### 📄 Relatórios
- ✅ **Filtros por período**: Hoje, Semana, Mês, Trimestre, Ano, Personalizado
- ✅ **Tipos de relatório**: Lavagens, Financeiro, Clientes, Estoque
- ✅ **Resumo automático** com cards de estatísticas
- ✅ **Impressão** em nova janela com layout otimizado

### 🔐 Painel Administrativo
- ✅ **Níveis de acesso**:
  - 👑 **Administrador** — Acesso total (Dashboard, Clientes, Lavagens, Estoque, Relatórios, Admin)
  - 🧑‍💼 **Gerente** — Estoque, Lavagens e Clientes
  - 👷 **Funcionário** — Lavagens e Clientes
- ✅ Gerenciamento de usuários (criar, editar, ativar/inativar)
- ✅ Senha com opção de não alterar ao editar

---

## 🛠️ Tecnologias Utilizadas

📌 Status do Projeto :

🚧 Em construção — Funcionalidades principais implementadas, melhorias contínuas em andamento.

🧠 Aprendizados : 

Durante o desenvolvimento deste projeto, aprofundei conhecimentos em:
Arquitetura SPA (Single Page Application) com JavaScript vanilla
Controle de estoque com baixa automática
Sistema de permissões e níveis de acesso
Geração de relatórios filtráveis por período
Validação de formulários em tempo real
Design responsivo com CSS puro
Integração frontend-backend com API REST
Uso de IA como ferramenta produtiva no desenvolvimento

📝 Licença :

Este projeto foi desenvolvido para fins de aprendizado e portfólio.

👤 Autor : Emerson Hugo Venceslau | 
https://www.linkedin.com/in/emerson-venceslau-9587bb2b7/
https://github.com/K4ts0



## 📁 Estrutura do Projeto
