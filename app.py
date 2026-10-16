import os
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, flash
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:1234@localhost:5432/coleta_produtos"
)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Nomes esperados das colunas:
# dados(codigo_interno, descricao, validade_atual, fabricacao_atual,
#       validade_coletada, fabricacao_coletada)
# gtins(codigo_interno, codigo_barras)

PENDENTES_SQL = text("""
    SELECT d.codigo_interno, d.descricao
    FROM dados d
    WHERE d.validade_coletada IS NULL
      AND d.fabricacao_coletada IS NULL
    ORDER BY d.codigo_interno
""")

def buscar_produto(codigo):
    """Busca primeiro por código interno e depois por código de barras."""
    with engine.connect() as conn:
        resultado = conn.execute(text("""
            SELECT d.codigo_interno, d.descricao,
                   d.validade_atual, d.fabricacao_atual,
                   d.validade_coletada, d.fabricacao_coletada
            FROM dados d
            WHERE CAST(d.codigo_interno AS TEXT) = :codigo
            LIMIT 1
        """), {"codigo": codigo}).mappings().first()

        if resultado:
            return dict(resultado)

        resultado = conn.execute(text("""
            SELECT d.codigo_interno, d.descricao,
                   d.validade_atual, d.fabricacao_atual,
                   d.validade_coletada, d.fabricacao_coletada
            FROM gtins g
            JOIN dados d ON d.codigo_interno = g.codigo_interno
            WHERE CAST(g.codigo_barras AS TEXT) = :codigo
            LIMIT 1
        """), {"codigo": codigo}).mappings().first()

        return dict(resultado) if resultado else None

@app.get("/")
def index():
    try:
        with engine.connect() as conn:
            produtos = conn.execute(PENDENTES_SQL).mappings().all()
        return render_template("index.html", produtos=produtos)
    except SQLAlchemyError:
        app.logger.exception("Erro ao consultar os produtos pendentes")
        return render_template("erro_banco.html"), 500

@app.post("/buscar")
def buscar():
    codigo = request.form.get("codigo", "").strip()
    if not codigo:
        flash("Leia ou digite um código de barras ou código interno.", "erro")
        return redirect(url_for("index"))

    try:
        produto = buscar_produto(codigo)
    except SQLAlchemyError:
        app.logger.exception("Erro ao pesquisar produto")
        flash("Não foi possível consultar o banco de dados.", "erro")
        return redirect(url_for("index"))

    if not produto:
        flash(f"Nenhum produto encontrado para o código {codigo}.", "erro")
        return redirect(url_for("index"))

    # Evita coletar novamente um produto que já tenha qualquer data preenchida.
    if produto["validade_coletada"] is not None or produto["fabricacao_coletada"] is not None:
        flash("Este produto já possui pelo menos uma data coletada e não está pendente.", "aviso")
        return redirect(url_for("index"))

    return render_template("coletar.html", produto=produto)

@app.post("/salvar")
def salvar():
    codigo_interno = request.form.get("codigo_interno", "").strip()
    fabricacao = request.form.get("fabricacao_coletada", "").strip()
    validade = request.form.get("validade_coletada", "").strip()

    if not codigo_interno or not fabricacao or not validade:
        flash("Preencha a fabricação e a validade coletadas.", "erro")
        return redirect(url_for("index"))

    try:
        fabricacao_data = date.fromisoformat(fabricacao)
        validade_data = date.fromisoformat(validade)
    except ValueError:
        flash("Data inválida. Confira os campos de data.", "erro")
        return redirect(url_for("index"))

    if validade_data < fabricacao_data:
        flash("A validade não pode ser anterior à data de fabricação.", "erro")
        produto = buscar_produto(codigo_interno)
        if produto:
            return render_template("coletar.html", produto=produto,
                                   fabricacao_digitada=fabricacao,
                                   validade_digitada=validade), 400
        return redirect(url_for("index"))

    try:
        with engine.begin() as conn:
            resultado = conn.execute(text("""
                UPDATE dados
                SET fabricacao_coletada = :fabricacao,
                    validade_coletada = :validade
                WHERE CAST(codigo_interno AS TEXT) = :codigo
                  AND fabricacao_coletada IS NULL
                  AND validade_coletada IS NULL
            """), {
                "fabricacao": fabricacao_data,
                "validade": validade_data,
                "codigo": codigo_interno
            })
            if resultado.rowcount == 0:
                flash("O produto não foi atualizado: pode já ter sido coletado.", "aviso")
                return redirect(url_for("index"))

        flash("Coleta salva com sucesso!", "sucesso")
        return redirect(url_for("index"))
    except SQLAlchemyError:
        app.logger.exception("Erro ao salvar a coleta")
        flash("Erro ao salvar no banco de dados. Confira a conexão e tente novamente.", "erro")
        return redirect(url_for("index"))

@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except SQLAlchemyError:
        return {"status": "erro", "detalhe": "Banco indisponível"}, 503

if __name__ == "__main__":
    # Para acessar de outro equipamento na rede local, use host 0.0.0.0.
    # Em produção, rode com um servidor WSGI e não ative o modo debug.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
