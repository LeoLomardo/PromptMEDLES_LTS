#!/usr/bin/env python3
# -*- coding: ISO-8859-1 -*-
import os
import traceback
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from db.models import buscar_jornada_por_id

# Carrega vari�veis de ambiente
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/prompt', methods=['POST'])
def handle_prompt():
    data = request.get_json(force=True)
    user_prompt = data.get("prompt", "").strip()
    patient_id = data.get("patient_id", "").strip()

    if not user_prompt or not patient_id:
        return jsonify({"error": "Campos 'prompt' e 'patient_id' s�o obrigat�rios."}), 400

    try:
        # Busca as observa��es do paciente
        registros = buscar_jornada_por_id(patient_id)
        if not registros:
            return jsonify({"resposta": "Nenhum dado encontrado para o paciente informado."})

        # Opcional: limitar o n�mero de registros se forem muitos
        registros = registros[-30:]

        # Monta o contexto textual com os dados do paciente
        contexto = "\n\n".join([
            f"[{r['data']}] {r['tipo']} - {r['observacao']} (Local: {r['local']}, Profissional: {r['profissional']}, Status: {r['status']}, Fonte: {r['fonte']})"
            for r in registros if r.get("observacao")
        ])

        # Prepara o prompt completo
        prompt_completo = f"""
Voc� � um assistente de sa�de analisando dados cl�nicos. Com base nas observa��es abaixo do paciente de ID {patient_id}, responda � pergunta do usu�rio.

DADOS DO PACIENTE:
{contexto}

PERGUNTA: {user_prompt}
        """

        # Chamada direta � OpenAI (modelo GPT-4o ou GPT-3.5-turbo)
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

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
