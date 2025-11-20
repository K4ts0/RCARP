# Sistema simples baseado em planilhas

## Como rodar
```bash
cd /mnt/data/sistema_planilhas_login
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
Acesse http://localhost:5000

Login padrão: **admin / admin123**

## Importação
- CSVs normalizados ficam em `data/clientes_mensais.csv` e `data/estoque_avancado.csv`.
- Para atualizar, use o formulário de upload na tela inicial ou o botão de reimportação.
- Colunas são normalizadas automaticamente (minúsculas, underline).
