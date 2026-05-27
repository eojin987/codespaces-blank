import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import google.generativeai as genai

app = Flask(__name__)
# async_mode='eventlet'을 추가해서 엔진을 강제 지정
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

my_api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=my_api_key)

# 사용 가능한 모델을 자동으로 찾아서 연결하는 코드
valid_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
model = genai.GenerativeModel(valid_models[0])
# 가해자 무리 조교 프롬프트 주입 (톤 다운 & 다중 역할)
persona_prompt = """
[시스템 설정: 너는 학교폭력 예방 시뮬레이션 게임의 '가해자 무리(주동자, 동조자1, 동조자2)' 역할이다.]
- 상황: 단톡방에서 특정 학생(피해자)을 은근히 조리돌림하는 중.
- 대화 상대(사용자): 방관하다가 개입하려는 다른 친구(방어자).
- 성격 및 태도(매우 중요): 사용자(방어자)에게 대놓고 화를 내거나 날카롭게 공격하지 마! 대신, 너희의 행동을 '단순한 장난'으로 포장하며, 말리는 사용자를 '진지충', '분위기 파악 못하는 애' 취급해. (예: "아 왜그래 장난인데 ㅋㅋ", "갑자기 진지빨고 그래", "너 혼자 예민하네")
- [절대 지켜야 할 규칙]
  1. 한 번 대답할 때 2~3개의 톡을 연달아 보내.
  2. 반드시 각 줄의 시작에 '주동자:', '동조자1:', '동조자2:' 중 하나를 붙여서 누가 말하는지 명시해. (예 -> 동조자1: 아 갑자기 분위기 씹선비 ㅋㅋㅋ)
  3. 피해자의 이름 대신 멸칭(쟤, 저새끼, 찐따)을 사용해.
"""

chat = model.start_chat(history=[
    {"role": "user", "parts": [persona_prompt]},
    {"role": "model", "parts": ["주동자: 야 ㅋㅋ 장난인데 왜구랭\n동조자1: ㅇㅈ 갑자기 분위기 쌉진지해지네\n동조자2: 아 씹선비 납셨네 ㅋㅋㅋ"]}
])

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def student_view():
    return render_template('student.html')

@app.route('/teacher')
def teacher_view():
    return render_template('teacher.html')

@socketio.on('submit_suggestion')
def handle_suggestion(data):
    emit('receive_suggestion', data, broadcast=True, include_self=False)

# 봇 응답을 분석해서 이름표를 다르게 붙여주는 기능
@socketio.on('send_to_bot')
def handle_send_to_bot(data):
    user_message = data['message']
    
    emit('chat_update', {'sender': '우리 반', 'message': user_message}, broadcast=True)
    
    try:
        response = chat.send_message(user_message)
        bot_reply = response.text
        
        for line in bot_reply.split('\n'):
            line = line.strip()
            if not line: continue
            
            sender_name = "주동자" # 기본값
            msg_text = line
            
            # '주동자: 내용' 형식을 쪼개서 발신자 이름과 내용 분리
            if ":" in line:
                parts = line.split(":", 1)
                if parts[0].strip() in ["주동자", "동조자1", "동조자2"]:
                    sender_name = parts[0].strip()
                    msg_text = parts[1].strip()
            
            emit('chat_update', {'sender': sender_name, 'message': msg_text}, broadcast=True)
    except ValueError:
            emit('chat_update', {'sender': '주동자', 'message': '뭐라는 거야 ㅡㅡ 장난하냐? 똑바로 말해'}, broadcast=True)
    except Exception as e:
        emit('chat_update', {'sender': '시스템', 'message': "오류가 발생했습니다: " + str(e)}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
