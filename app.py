#!/usr/bin/env python3
# -*- coding: ISO-8859-1 -*-
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from openai import OpenAI
from functools import wraps
from db.models import buscar_jornada_por_id, filtrar_pacientes, buscar_convenios, buscar_profissionais, busca_conjunto
import os, traceback

import io
import base64
import matplotlib
matplotlib.use('Agg') # Importante: usa um backend nao-interativo para o Matplotlib
import matplotlib.pyplot as plt
from collections import Counter # A IA pode usar, entao disponibilizamos
import pandas as pd
from datetime import datetime
import builtins
import re
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
app = Flask(__name__)
app.config['SESSION_PERMANENT'] = False

app.secret_key = os.getenv("SECRET_KEY", "uma-chave-secreta")

client = OpenAI(api_key=OPENAI_API_KEY)

# Carrega usuarios validos a partir do .env
admin_user = os.getenv("ADMIN_CRED")
admin_pass = os.getenv("ADMIN_SENHA")
leo_user = os.getenv("LEO_CRED")
leo_pass = os.getenv("LEO_SENHA")
if not admin_user or not admin_pass:
    raise RuntimeError("ADMIN_CRED ou ADMIN_SENHA nao estao definidos no .env")

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
        return render_template('login.html', erro="Usuario ou senha invalidos")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')


#bloquear cache no navegador
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
        return jsonify({"error": "Campos 'prompt' e 'patient_id' sao obrigatorios."}), 400

    try:
        registros = buscar_jornada_por_id(patient_id)
        if not registros:
            return jsonify({"resposta": "Nenhum dado encontrado para o paciente informado."})

        registros = registros[-1000:]
        contexto = "\n\n".join([
            f"[{r['data']}] {r['descricao']} "
            f"(CPF: {r['cpf']}"
            f"Conjunto: {r['conjunto']}, Profissional: {r['nome_profissional']}, "
            f"Convenio: {r['nome_convenio']}, Fonte: {r['fonte']})"
            f"Data de Nascimento: {r['data_nascimento']}"
            for r in registros if r.get("descricao")
        ])

        prompt_completo = f"""
Voce e um assistente de saude analisando dados clinicos. Com base nas observacoes abaixo do paciente de ID {patient_id}, responda a pergunta do usuario, NAO ESCREVA O NOME DO PACIENTE NUNCA. Escreva o texto com formatacao markdown.
Apenas quando o usuario explicitamente solicitar um grafico, gere um codigo em Python para plota-lo.

Quando (e somente quando) o usuario pedir um grafico, responda **apenas** com UM bloco de codigo Python entre crases triplas, no formato:
- Gere APENAS o corpo do codigo em Python que prepara o grafico.
- NUNCA inclua "import" statements.
- NUNCA chame `plt.show()` ou `plt.savefig()`. O sistema se encarregara de exibir a imagem.
- As seguintes variaveis ja estao disponiveis: `plt` (para graficos), `Counter` (para contagens), e `datetime` (a classe para manipular datas).
- Para converter uma string de data, use `datetime.fromisoformat(...)` diretamente.

DADOS DO PACIENTE:
{contexto}

PERGUNTA: {user_prompt}
"""

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Voce e um assistente medico que analisa prontuarios clinicos e responde perguntas com base em observacaes do paciente."},
                {"role": "user", "content": prompt_completo}
            ],
            temperature=0.2
        )

        resposta = response.choices[0].message.content.strip()
        return jsonify({"resposta": resposta})

    except Exception as e:
        print("Erro completo:", traceback.format_exc())
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


@app.route('/plot', methods=['POST'])
@login_required
def plot_graph():
    data = request.get_json(force=True)
    raw = (data.get('code') or '').strip()

    if not raw:
        return jsonify({"error": "Nenhum codigo fornecido."}), 400

    try:
        # 1) Extrai o primeiro bloco ```python ... ``` ou ``` ... ```
        m = re.search(r"```(?:python)?\s*(.+?)```", raw, flags=re.S|re.I)
        code = m.group(1).strip() if m else raw  # se não houver crases, usa o texto todo mesmo

        # 2) Remove imports e chamadas proibidas
        lines = code.splitlines()
        safe_code_lines = []
        for line in lines:
            s = line.strip()
            if s.startswith("import ") or s.startswith("from "):
                continue
            if "plt.show(" in s.replace(" ", "") or "plt.savefig(" in s.replace(" ", ""):
                continue
            safe_code_lines.append(line)
        safe_code = "\n".join(safe_code_lines).strip()

        # 3) Se o modelo colou varias instrucoes na mesma linha, adiciona quebras antes de plt.*
        #    Exemplos: ") plt.", "] plt.", "} plt." ? nova linha antes de plt.
        safe_code = re.sub(r"\)\s+plt\.", r")\nplt.", safe_code)
        safe_code = re.sub(r"\]\s+plt\.", r"]\nplt.", safe_code)
        safe_code = re.sub(r"\}\s+plt\.", r"}\nplt.", safe_code)
        # Também separa comandos por ';' se houver
        if "; " in safe_code:
            safe_code = safe_code.replace("; ", ";\n")

        # 4) Import guard
        original_import = builtins.__import__
        blacklist = ['os', 'sys', 'subprocess', 'shutil', 'requests', 'socket', 'http']

        def safe_importer(name, globals=None, locals=None, fromlist=(), level=0):
            for module_name in blacklist:
                if name.startswith(module_name):
                    raise ImportError(f"A importacao do modulo '{name}' nao e permitida.")
            return original_import(name, globals, locals, fromlist, level)

        safe_builtins_dict = {
            "print": print, "len": len, "range": range, "min": min, "max": max,
            "sum": sum, "abs": abs, "round": round, "sorted": sorted, "list": list,
            "dict": dict, "set": set, "tuple": tuple, "str": str, "int": int,
            "float": float, "bool": bool, "enumerate": enumerate, "zip": zip,
            "__import__": safe_importer,
        }

        safe_globals = {
            "__builtins__": safe_builtins_dict,
            "plt": plt,
            "pd": pd,
            "Counter": Counter,
            "datetime": datetime,
        }

        plt.clf()
        exec(safe_code, safe_globals)

        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        buf.close()

        return jsonify({"image_base64": image_base64})

    except Exception as e:
        print("Erro ao executar codigo do grafico:", traceback.format_exc())
        return jsonify({"error": f"Erro ao gerar o grafico: {str(e)}"}), 500


@app.route('/convenios', methods=['GET'])
@login_required
def get_convenios():
    try:
        convenios = buscar_convenios()
        return jsonify(convenios)
    except Exception as e:
        print("Erro ao buscar convenios:", traceback.format_exc())
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@app.route('/profissionais', methods=['GET'])
@login_required
def get_profissionais():
    try:
        profissionais = buscar_profissionais()
        return jsonify(profissionais)
    except Exception as e:
        print("Erro ao buscar profissionais:", traceback.format_exc())
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500


@app.route('/conjuntos', methods=['GET'])
@login_required
def get_conjuntos():
    try:
        conjuntos = busca_conjunto()
        return jsonify(conjuntos)
    except Exception as e:
        print("Erro ao buscar conjuntos:", traceback.format_exc())
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

@app.route('/filter', methods=['POST'])
@login_required
def filter_patients():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Requisição inválida."}), 400

    try:
        idade_min_str = data.get('idade_min')
        idade_max_str = data.get('idade_max')
        idade_min = int(idade_min_str) if idade_min_str else None
        idade_max = int(idade_max_str) if idade_max_str else None

        convenios = data.get('convenios')
        profissionais = data.get('profissionais')
        conjuntos = data.get('conjuntos')

        if idade_min is None and not convenios and not profissionais and not conjuntos:
            return jsonify({"error": "Por favor, forneça ao menos um critério de busca."}), 400
        
        if (idade_min is not None and idade_max is None) or (idade_min is None and idade_max is not None):
            return jsonify({"error": "Para filtrar por idade, por favor, preencha tanto a idade mínima quanto a máxima."}), 400

        pacientes_encontrados = filtrar_pacientes(idade_min, idade_max, convenios, profissionais, conjuntos)
        
        if not pacientes_encontrados:
            resposta = f"Nenhum paciente encontrado com os filtros aplicados."
        else:

            total_pacientes = len(pacientes_encontrados)
            total_eventos_filtrados = sum(paciente['total_eventos'] for paciente in pacientes_encontrados)
            
            filtros_usados_list = []
            if idade_min is not None and idade_max is not None:
                filtros_usados_list.append(f"idade entre {idade_min} e {idade_max} anos")
            if convenios:
                filtros_usados_list.append(f"convênios: {', '.join(convenios)}")
            if profissionais:
                filtros_usados_list.append(f"médicos: {', '.join(profissionais)}")
            if conjuntos:
                filtros_usados_list.append(f"conjuntos: {', '.join(conjuntos)}")
            
            filtros_usados = f"({', '.join(filtros_usados_list)})" if filtros_usados_list else ""

            response_parts = []
            response_parts.append(f"### Pacientes Encontrados {filtros_usados}:\n\n")
            
            response_parts.append(f"**Resumo da Busca:**\n")
            response_parts.append(f"* **Total de Pacientes Encontrados:** {total_pacientes}\n")
            response_parts.append(f"* **Total de Eventos (destes pacientes):** {total_eventos_filtrados}\n\n")

            response_parts.append("| ID Paciente | Idade | N° de Eventos |\n")
            response_parts.append("|----------------------|-------|---------------|\n")
            
            for paciente in pacientes_encontrados:
                patient_id = paciente['id_paciente']
                linha = f"| <span class='patient-id-link' data-id='{patient_id}'>{patient_id}</span> | {int(paciente['idade_calculada'])} | {paciente['total_eventos']} |\n"
                response_parts.append(linha)
            
            resposta = "".join(response_parts)
        
        return jsonify({"resposta": resposta})

    except (ValueError, TypeError):
        return jsonify({"error": "Valores de idade inválidos. Por favor, insira apenas números."}), 400
    except Exception as e:
        print("Erro completo no filtro:", traceback.format_exc())
        return jsonify({"error": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)