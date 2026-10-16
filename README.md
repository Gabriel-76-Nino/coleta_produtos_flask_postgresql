# Coleta de produtos — Flask + PostgreSQL

Aplicação web para conferir produtos e registrar fabricação e validade usando código interno ou código de barras GTIN. Compatível com coletores Honeywell configurados como teclado (keyboard wedge).

## 1. Criar o banco de dados

No PostgreSQL, crie o banco (se ainda não existir):

```sql
CREATE DATABASE coleta_produtos;
```

Depois conecte-se ao banco `coleta_produtos` e execute o conteúdo do arquivo `schema.sql`. Ele cria as tabelas `dados` e `gtins`, a chave estrangeira e os índices. Não execute `CREATE DATABASE` dentro de uma transação.

Você também pode executar o arquivo usando `psql`:

```bash
psql -U postgres -d coleta_produtos -f schema.sql
```

No Windows, o `psql` pode estar disponível no SQL Shell (psql) instalado junto com o PostgreSQL.

## 2. Estrutura criada

- `dados`: `codigo_interno` (PK), `descricao`, `validade_atual`, `fabricacao_atual`, `validade_coletada`, `fabricacao_coletada`
- `gtins`: `codigo_interno` (FK para `dados.codigo_interno`), `codigo_barras`

Códigos são texto para preservar zeros à esquerda. Um produto pode ter mais de um GTIN. As colunas de coleta são `DATE` e começam como `NULL`.

## 3. Instalar a aplicação no Windows

Na pasta do projeto, abra PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg://postgres:SUA_SENHA@localhost:5432/coleta_produtos"
$env:SECRET_KEY="substitua-por-uma-chave-aleatoria"
python app.py
```

Se o PowerShell bloquear a ativação do ambiente virtual, você pode executar diretamente:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

## 4. Instalar no Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://postgres:SUA_SENHA@localhost:5432/coleta_produtos'
export SECRET_KEY='substitua-por-uma-chave-aleatoria'
python app.py
```

Abra `http://localhost:5000` no navegador.

## 5. Inserir produtos

Cadastre primeiro o produto em `dados`; depois associe um ou mais códigos de barras em `gtins`.

Exemplo de teste (use apenas se esses códigos de exemplo não existirem):

```sql
INSERT INTO dados (codigo_interno, descricao, validade_atual, fabricacao_atual)
VALUES ('1001', 'Produto de teste', '2027-12-31', '2026-01-01');

INSERT INTO gtins (codigo_interno, codigo_barras)
VALUES ('1001', '7890000000012');
```

## 6. Usar o coletor Honeywell

Inicie a aplicação no computador servidor. No Honeywell conectado à mesma rede, abra `http://IP_DO_SERVIDOR:5000`. Configure o leitor para modo teclado e, de preferência, para enviar Enter ao final da leitura.

Permita a porta TCP 5000 apenas na rede local confiável. Para produção, use um servidor WSGI, HTTPS e autenticação; o servidor integrado do Flask é indicado para testes e uso interno simples.

## Regras de coleta

- A lista mostra produtos em que `validade_coletada IS NULL AND fabricacao_coletada IS NULL`.
- A pesquisa tenta o código interno e depois o GTIN.
- A tela exige as duas datas.
- Impede validade anterior à fabricação.
- Atualiza os dois campos em uma transação e impede que uma coleta concorrente sobrescreva outra.
- Após salvar, a lista de pendências é atualizada.
