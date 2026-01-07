# BOJ 인증 봇

매일 백준 문제 풀이를 인증하는 카카오톡 챗봇

## 기능

- 백준 아이디 등록
- 일일 인증 현황 확인
- solved.ac API 연동

## Railway 배포 방법

### 1. GitHub에 코드 올리기

```bash
cd /Users/ryu/Desktop/project/BOJBot

# Git 초기화 (아직 안 했다면)
git init

# 파일 추가
git add .
git commit -m "Initial commit"

# GitHub에 푸시 (저장소 먼저 만들어야 함)
git remote add origin https://github.com/your-username/bojbot.git
git branch -M main
git push -u origin main
```

### 2. Railway 배포

1. https://railway.app 접속
2. GitHub 계정으로 로그인
3. **New Project** 클릭
4. **Deploy from GitHub repo** 선택
5. BOJBot 저장소 선택
6. 자동으로 배포 시작

### 3. URL 확인

1. 배포 완료 후 **Settings** → **Networking**
2. **Generate Domain** 클릭
3. 생성된 URL 복사 (예: `https://bojbot-production.up.railway.app`)

### 4. 카카오 챗봇에 URL 등록

1. https://chatbot.kakao.com 접속
2. **스킬** → **register_user** 스킬 편집
3. URL 변경:
   ```
   https://your-app.up.railway.app/kakao/register
   ```
4. **check_status** 스킬도 동일하게:
   ```
   https://your-app.up.railway.app/kakao/status
   ```

### 5. 테스트

카카오톡에서 챗봇 채널로:
```
등록 백준아이디
현황
```

## 로컬 테스트

```bash
# 패키지 설치
pip install -r requirements.txt

# 서버 실행
python server.py

# 다른 터미널에서 테스트
curl -X POST http://localhost:5000/kakao/register \
  -H "Content-Type: application/json" \
  -d '{
    "userRequest": {"user": {"id": "test123"}},
    "action": {"params": {"boj_id": "koosaga"}}
  }'
```

## 파일 구조

```
BOJBot/
├── server.py          # Flask 서버 (카카오 챗봇용)
├── bot.py             # CLI 도구 (로컬 테스트용)
├── requirements.txt   # Python 패키지
├── Procfile          # Railway 실행 설정
├── runtime.txt       # Python 버전
├── .gitignore        # Git 제외 파일
└── data/
    └── users.json    # 유저 데이터 (자동 생성)
```

## 문제 해결

### Railway 배포 실패
- **Logs** 탭에서 에러 확인
- `requirements.txt` 파일 확인
- Python 버전 확인 (`runtime.txt`)

### 카카오 챗봇 응답 없음
- Railway URL이 정확한지 확인
- `/health` 엔드포인트로 서버 상태 확인: `https://your-app.up.railway.app/health`
- 카카오 챗봇 스킬 URL이 올바른지 확인

### 데이터가 사라짐
- Railway는 재배포 시 파일이 초기화될 수 있음
- 장기적으로는 PostgreSQL 같은 DB 추가 필요
