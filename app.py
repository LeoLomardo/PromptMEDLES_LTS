#!/usr/bin/env python3
# -*- coding: ISO-8859-1 -*-
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from openai import OpenAI
from functools import wraps
from db.models import buscar_jornada_por_id
import os, traceback

# --- NOVAS IMPORTA��ES ---
import io
import base64
import matplotlib
matplotlib.use('Agg') # Importante: usa um backend n�o-interativo para o Matplotlib
import matplotlib.pyplot as plt
from collections import Counter # A IA pode usar, ent�o disponibilizamos

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
app = Flask(__name__)
app.config['SESSION_PERMANENT'] = False

app.secret_key = os.getenv("SECRET_KEY", "uma-chave-secreta")

client = OpenAI(api_key=OPENAI_API_KEY)

# Carrega usu�rios v�lidos a partir do .env
admin_user = os.getenv("ADMIN_CRED")
admin_pass = os.getenv("ADMIN_SENHA")
leo_user = os.getenv("LEO_CRED")
leo_pass = os.getenv("LEO_SENHA")
if not admin_user or not admin_pass:
    raise RuntimeError("ADMIN_CRED ou ADMIN_SENHA n�o est�o definidos no .env")

USERS = {
    admin_user: admin_pass,
    leo_user: leo_pass
}

# Decorator para proteger rotas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if USERS.get(u) == p:
            session['user'] = u
            return redirect(url_for('index'))
        return render_template('login.html', erro="Usu�rio ou senha inv�lidos")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')


#tentativa de bloquear cache do no navegador
@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/prompt', methods=['POST'])
@login_required
def handle_prompt():
    data = request.get_json(force=True)
    user_prompt = data.get("prompt", "").strip()
    patient_id = data.get("patient_id", "").strip()

    if not user_prompt or not patient_id:
        return jsonify({"error": "Campos 'prompt' e 'patient_id' s�o obrigat�rios."}), 400

    try:
        registros = buscar_jornada_por_id(patient_id)
        if not registros:
            return jsonify({"resposta": "Nenhum dado encontrado para o paciente informado."})

        registros = registros[-1000:]
        contexto = "\n\n".join([
            f"[{r['data_registro']}] {r['descricao']} "
            f"(CPF: {r['cpf']}, Idade: {r['idade']}, "
            f"Conjunto: {r['conjunto']}, Profissional: {r['nome_profissional']}, "
            f"Conv�nio: {r['nome_convenio']}, Fonte: {r['fonte']})"
            f"Data de Nascimento: {r['data_nascimento']}"
            for r in registros if r.get("descricao")
        ])

        prompt_completo = f"""
Voc� � um assistente de sa�de analisando dados cl�nicos. Com base nas observa��es abaixo do paciente de ID {patient_id}, responda � pergunta do usu�rio. 
Apenas quando o usu�rio explicitamente solicitat um gr�fico, gere um c�digo em Python para plot�-lo.
IMPORTANTE: Gere APENAS o corpo do c�digo, sem incluir `import matplotlib.pyplot as plt` ou `from collections import Counter`. As vari�veis `plt` e `Counter` j� estar�o dispon�veis para uso direto no seu c�digo.

DADOS DO PACIENTE:
{contexto}

PERGUNTA: {user_prompt}
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Voc� � um assistente m�dico que analisa prontu�rios cl�nicos e responde perguntas com base em observa��es do paciente."},
                {"role": "user", "content": prompt_completo}
            ],
            temperature=0.2
        )

        resposta = response.choices[0].message.content.strip()
        return jsonify({"resposta": resposta})

    except Exception as e:
        print("Erro completo:", traceback.format_exc())
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

# --- NOVA ROTA PARA GERAR O GR�FICO ---
@app.route('/plot', methods=['POST'])
@login_required
def plot_graph():
    data = request.get_json(force=True)
    code = data.get('code')

    if not code:
        return jsonify({"error": "Nenhum c�digo fornecido."}), 400

    try:
        # Ambiente seguro para execu��o
        safe_globals = {
            'plt': plt,
            'Counter': Counter,
            '__builtins__': {
                'print': print,
                'list': list,
                'dict': dict,
                'str': str,
                'int': int,
                'float': float,
                'len': len
             }
        }
        
        # Limpa qualquer figura anterior
        plt.clf()

        # Executa o c�digo fornecido
        exec(code, safe_globals)

        # Salva o gr�fico em um buffer de mem�ria
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)

        # Codifica a imagem em Base64 para enviar via JSON
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        
        buf.close()

        return jsonify({"image_base64": image_base64})

    except Exception as e:
        print("Erro ao executar c�digo do gr�fico:", traceback.format_exc())
        return jsonify({"error": f"Erro ao gerar o gr�fico: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)