from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secret_key'  # Alterar para uma chave secreta adequada

DATABASE = 'questions.db'

# Função para inicializar o banco de dados
def init_db():
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('professor', 'editor'))
        )''')
        cur.execute('''CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            enunciado TEXT NOT NULL,
            imagem TEXT,
            ano INTEGER NOT NULL CHECK(ano BETWEEN 6 AND 12),
            dificuldade INTEGER NOT NULL CHECK(dificuldade IN (1, 2, 3)),
            disciplina TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            gabarito TEXT NOT NULL
        )''')
        con.commit()

# Função para adicionar usuário padrão
def add_default_user():
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM users WHERE username = ?', ('admin',))
        user = cur.fetchone()
        if not user:
            cur.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                        ('admin', 'admin', 'editor'))
            con.commit()

# Rota para a página de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cur.fetchone()
        con.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            return redirect(url_for('index'))
        else:
            flash('Login ou senha incorretos')
    return render_template('login.html')

# Rota para a página principal
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', role=session['role'])

# Rota para adicionar questão
@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    if 'username' not in session or session['role'] != 'editor':
        return redirect(url_for('index'))
    if request.method == 'POST':
        enunciado = request.form['enunciado']
        imagem = request.files['imagem']
        ano = request.form['ano']
        dificuldade = request.form['dificuldade']
        disciplina = request.form['disciplina']
        conteudo = request.form['conteudo']
        gabarito = request.form['gabarito']
        imagem_path = None
        if imagem:
            # Construir o caminho do arquivo usando os.path.join para garantir as barras corretas
            imagem_path = os.path.join('static', 'uploads', imagem.filename)
            # Substituir barras invertidas por barras normais
            imagem_path = imagem_path.replace('\\', '/')
            # Salvar a imagem no caminho correto
            imagem.save(imagem_path)
        with sqlite3.connect(DATABASE) as con:
            cur = con.cursor()
            cur.execute('INSERT INTO questions (enunciado, imagem, ano, dificuldade, disciplina, conteudo, gabarito) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (enunciado, imagem_path, ano, dificuldade, disciplina, conteudo, gabarito))
            con.commit()
        return redirect(url_for('index'))
    return render_template('add_question.html')

# Rota para editar questão
@app.route('/edit_question/<int:id>', methods=['GET', 'POST'])
def edit_question(id):
    if 'username' not in session or session['role'] != 'editor':
        return redirect(url_for('index'))
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    if request.method == 'POST':
        enunciado = request.form['enunciado']
        imagem = request.files['imagem']
        ano = request.form['ano']
        dificuldade = request.form['dificuldade']
        disciplina = request.form['disciplina']
        conteudo = request.form['conteudo']
        gabarito = request.form['gabarito']
        imagem_path = None
        if imagem:
            # Construir o caminho do arquivo usando os.path.join para garantir as barras corretas
            imagem_path = os.path.join('static', 'uploads', imagem.filename)
            # Substituir barras invertidas por barras normais
            imagem_path = imagem_path.replace('\\', '/')
            # Salvar a imagem no caminho correto
            imagem.save(imagem_path)
        else:
            cur.execute('SELECT imagem FROM questions WHERE id = ?', (id,))
            imagem_path = cur.fetchone()[0]
        cur.execute('UPDATE questions SET enunciado = ?, imagem = ?, ano = ?, dificuldade = ?, disciplina = ?, conteudo = ?, gabarito = ? WHERE id = ?',
                    (enunciado, imagem_path, ano, dificuldade, disciplina, conteudo, gabarito, id))
        con.commit()
        return redirect(url_for('index'))
    cur.execute('SELECT * FROM questions WHERE id = ?', (id,))
    question = cur.fetchone()
    con.close()
    return render_template('edit_question.html', question=question)

# Rota para remover questão
@app.route('/delete_question/<int:id>')
def delete_question(id):
    if 'username' not in session or session['role'] != 'editor':
        return redirect(url_for('index'))
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        cur.execute('DELETE FROM questions WHERE id = ?', (id,))
        con.commit()
    return redirect(url_for('index'))

# Rota para visualizar questões
@app.route('/view_questions')
def view_questions():
    if 'username' not in session:
        return redirect(url_for('login'))

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    # Consultas para buscar critérios únicos
    cur.execute('SELECT DISTINCT disciplina FROM questions')
    disciplinas = cur.fetchall()

    cur.execute('SELECT DISTINCT ano FROM questions ORDER BY ano')
    anos = cur.fetchall()

    cur.execute('SELECT DISTINCT dificuldade FROM questions ORDER BY dificuldade')
    dificuldades = cur.fetchall()

    # Parâmetros de filtragem
    disciplina = request.args.get('disciplina')
    ano = request.args.get('ano')
    dificuldade = request.args.get('dificuldade')
    conteudo = request.args.get('conteudo')

    # Consultar conteúdos únicos com base nos filtros selecionados
    query = 'SELECT DISTINCT conteudo FROM questions WHERE 1=1'
    params = []
    if disciplina:
        query += ' AND disciplina = ?'
        params.append(disciplina)
    if ano:
        query += ' AND ano = ?'
        params.append(ano)
    if dificuldade:
        query += ' AND dificuldade = ?'
        params.append(dificuldade)
    cur.execute(query, params)
    conteudos = cur.fetchall()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(
            conteudos=[cont[0] for cont in conteudos],
            anos=[year[0] for year in anos],
            dificuldades=[dif[0] for dif in dificuldades]
        )

    # Construção da consulta SQL baseada nos parâmetros recebidos
    query = 'SELECT * FROM questions WHERE 1=1'
    params = []

    if disciplina:
        query += ' AND disciplina = ?'
        params.append(disciplina)
    if ano:
        query += ' AND ano = ?'
        params.append(ano)
    if dificuldade:
        query += ' AND dificuldade = ?'
        params.append(dificuldade)
    if conteudo:
        query += ' AND conteudo = ?'
        params.append(conteudo)

    cur.execute(query, params)
    questions = cur.fetchall()
    con.close()

    return render_template('view_questions.html', questions=questions, disciplinas=disciplinas, anos=anos, dificuldades=dificuldades, conteudos=conteudos, selected_disciplina=disciplina, selected_ano=ano, selected_dificuldade=dificuldade, selected_conteudo=conteudo)


# Rota para logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Inicializando o banco de dados
init_db()

if __name__ == '__main__':
    add_default_user()
    app.run(debug=True)
